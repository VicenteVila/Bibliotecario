"""Tests del agregado y del reparto de las preguntas no respondibles.

Este harness ya cometió dos veces el mismo tipo de bug: descartar de la media
lo que no se pudo medir (judges no parseables) y mezclar poblaciones
incomparables (provenance contra un doc_id en preguntas multi-paper). Aquí se
ciñan las dos cosas.
"""
import json
import sys

import pytest

from evals import eval_end2end as H


def _row(id, judge=None, unanswerable=False, difficulty="media", abstained=None):
    return {"id": id, "judge": judge, "judge_error": None, "unanswerable": unanswerable,
            "difficulty": difficulty, "cite_precision": 1.0, "cite_coverage": 1.0,
            "answer_has_cite": True, "truncated": False, "fallback": False,
            "latency_s": 10, "judge_usage": {"total_tokens": 100},
            "agent_usage": {"total_tokens": 1000, "calls": 5, "calls_tokens_unknown": 0},
            "abstained": abstained, "fabricated_value": None}


def test_unanswerable_never_enters_judge_mean():
    """Una abstención correcta no puede hundir la media de 1-5."""
    rows = [_row("a1", 5), _row("a2", 4),
            _row("u1", None, unanswerable=True, abstained=True),
            _row("u2", None, unanswerable=True, abstained=False)]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["judge_mean"] == 4.5
    assert agg["n_answerable"] == 2
    assert agg["n_unanswerable"] == 2


def test_unparseable_judge_counts_as_zero_not_discarded():
    rows = [_row("a1", 5), _row("a2", None)]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["judge_mean"] == 2.5          # (5+0)/2, no 5.0
    assert agg["n_judge_errors"] == 1
    assert agg["n_scored"] == 1


def test_abstention_only_over_decided():
    """Si el juez de abstención no parsea, no se cuenta como "no se abstuvo"."""
    rows = [_row("u1", None, unanswerable=True, abstained=None),
            _row("u2", None, unanswerable=True, abstained=True),
            _row("u3", None, unanswerable=True, abstained=False)]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["abstain_rate"] == 0.5        # 1 de 2 decididas
    assert agg["n_abstain_decided"] == 2
    assert agg["n_abstain_errors"] == 1
    # judge_mean existe pero vacío: no se calcula sobre abstenciones.
    assert agg["judge_mean"] is None


def test_by_difficulty_covers_all_three_levels():
    rows = [_row("a1", 5, difficulty="facil"), _row("a2", 3, difficulty="media"),
            _row("a3", 1, difficulty="dificil"), _row("a4", None, difficulty="dificil")]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["by_difficulty"] == {"facil": 5.0, "media": 3.0, "dificil": 0.5}


def test_agent_tokens_are_summed_and_median_latency_reported():
    rows = [_row("a1", 5), _row("a2", 4)]
    rows[1]["latency_s"] = 30
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["agent_tokens_total"] == 2000
    assert agg["agent_calls_total"] == 10
    assert agg["judge_tokens_total"] == 200
    assert agg["latency_median_s"] == 30


def test_run_one_routes_unanswerable_to_abstention_judge(monkeypatch):
    """La garantía clave: una no respondible NUNCA se puntúa con la rúbrica 1-5."""
    calls = {"abstain": 0, "score": 0}

    monkeypatch.setattr(H.LLM, "reset_usage", lambda: None)
    monkeypatch.setattr(H.LLM, "usage_totals",
                        lambda: {"total_tokens": 1, "calls": 1, "calls_tokens_unknown": 0})
    monkeypatch.setattr(H.LOOP, "run",
                        lambda q, max_turns=4, isolated=False: {"answer": "no consta en el corpus",
                                                "evidence": [], "turns": 1})

    def fake_abstain(question, answer, **kw):
        calls["abstain"] += 1
        return {"abstained": True, "fabricated_value": None, "justification": "",
                "usage": {}, "error": None}

    def fake_judge(question, reference, answer, **kw):
        calls["score"] += 1
        return {"score": 1, "verdict": "", "model": "m", "usage": {}, "error": None}

    monkeypatch.setattr(H, "judge_abstention", fake_abstain)
    monkeypatch.setattr(H, "judge", fake_judge)

    row = H.run_one({"id": "u1", "question": "q", "unanswerable": True,
                     "answerable_docs": []}, turns=4)
    assert calls == {"abstain": 1, "score": 0}
    assert row["abstained"] is True
    assert row["judge"] is None

    row = H.run_one({"id": "a1", "question": "q", "reference": "r",
                     "answerable_docs": [1]}, turns=4)
    assert calls == {"abstain": 1, "score": 1}
    assert row["judge"] == 1
    assert row["abstained"] is None


def test_empty_input_does_not_divide_by_zero():
    agg = H.aggregate([], turns=4, retries=1)
    assert agg["n"] == 0
    assert agg["judge_mean"] is None
    assert agg["latency_median_s"] is None


def test_save_keeps_meta(tmp_path):
    p = tmp_path / "r.json"
    H.save([_row("a1", 5)], {"n": 1}, p, {"run": "r1"})
    d = json.loads(p.read_text())
    assert d["meta"]["run"] == "r1"
    assert d["rows"][0]["id"] == "a1"


@pytest.mark.parametrize("golden", ["golden_qa.jsonl", "golden_blind_qa.jsonl"])
def test_both_goldens_parse_and_declare_answerable_docs(golden):
    rows = [json.loads(l) for l in (H.EVALS / golden).read_text().splitlines() if l.strip()]
    assert rows
    for r in rows:
        assert "answerable_docs" in r
        if not r.get("unanswerable"):
            assert r["answerable_docs"]

def test_reanudar_no_pierde_filas(tmp_path, monkeypatch):
    """Reanudar una run debe conservar lo ya calculado.

    Regresión real: emit() solo escribía las filas de la sesión en curso, así que
    al reanudar tras una interrupción desaparecían las anteriores. Se perdieron
    4 preguntas de 40 sin que el agregado lo indicara.
    """
    prev = {"id": "pearl-b1", "judge": 5, "judge_error": None, "unanswerable": False,
            "difficulty": "facil", "cite_precision": 1.0, "cite_coverage": 1.0,
            "answer_has_cite": True, "truncated": False, "fallback": False,
            "latency_s": 5, "judge_usage": {}, "agent_usage": {}, "abstained": None,
            "fabricated_value": None}
    rp = tmp_path / "r.json"
    rp.write_text(json.dumps({"rows": [prev]}))

    # pearl-b1 ya está hecho; solo pearl-b2 se calcula en esta sesión.
    monkeypatch.setattr(sys, "argv", ["eval_end2end.py", "--golden", "golden_blind_qa.jsonl",
                                      "--ids", "pearl-b1,pearl-b2", "--turns", "4",
                                      "--out", str(rp)])
    monkeypatch.setattr(H, "run_one", lambda q, turns: {**prev, "id": q["id"],
                                                        "judge": 3, "difficulty": "media"})
    H.main()
    d = json.loads(rp.read_text())
    assert [r["id"] for r in d["rows"]] == ["pearl-b1", "pearl-b2"]
    assert d["aggregate"]["n"] == 2
    assert d["aggregate"]["judge_mean"] == 4.0


def test_looks_abstained_detecta_y_no_inventa():
    from evals.eval_end2end import looks_abstained as la
    assert la("No se encontró evidencia específica en los papers ingeridos")
    assert la("The corpus does not explicitly report the seed")
    assert la("insufficient evidence in the retrieved chunks")
    assert not la("PEARL achieves 8.67% on WN18RR [1:30]")
    assert not la("")


def test_abstencion_falsa_se_mide_aparte():
    """Respondibles en las que el agente se abstiene: retrieval fallido, no skill."""
    rows = [_row("a1", 5), _row("a2", 1), _row("a3", 4), _row("a4", 3)]
    for r in (rows[1], rows[3]):
        r["looks_abstained"] = True
    rows[0]["looks_abstained"] = False
    rows[2]["looks_abstained"] = False
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["false_abstention_rate"] == 0.5
    assert sorted(agg["false_abstention_ids"]) == ["a2", "a4"]
    assert agg["answer_rate_on_answerable"] == 0.5
    # Y no debe alterar la media de calidad: sigue siendo 4.5.
    assert agg["judge_mean"] == 3.25


def test_eval_arranca_aislado_de_lecciones():
    """Guardián: si alguien quita isolated=True, el prompt se contaminaría."""
    import inspect

    from evals import eval_end2end as E
    src = inspect.getsource(E.run_one)
    assert "isolated=True" in src, "eval_end2end.run_one debe llamar a LOOP.run con isolated=True"


def test_isolated_no_escribe_leccion_ni_las_lectura(monkeypatch):
    """isolated=True: ni save_lesson ni lectura de la tabla lessons."""
    import bibliotecario.agent.loop as L

    called = []
    monkeypatch.setattr(L.REF, "save_lesson", lambda *a, **k: called.append(a))
    monkeypatch.setattr(L, "load_lessons", lambda *a, **k: called.append(("read", a)) or "LECCION")
    monkeypatch.setattr(L, "generate", lambda *a, **k: '{"tool":"search_papers","args":{"query":"x"}}')
    monkeypatch.setattr(L, "_toolish", lambda *a, **k: True)
    monkeypatch.setattr(L, "parse_tool_call", lambda *a, **k: ("search_papers", {"query": "x"}))

    L.run("pregunta de prueba", max_turns=1, isolated=True)
    assert called == [], f"isolated no debe tocar lessons, pero: {called}"


def test_harness_es_por_hilo():
    """Con --workers 4 las preguntas paralelas no pueden compartir harness."""
    import threading

    from bibliotecario.harness.runtime import get_harness
    seen = []

    def grab():
        seen.append(get_harness())

    ts = [threading.Thread(target=grab) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len({id(h) for h in seen}) == 4, "cada hilo debe tener su harness"
    # El hilo principal conserva el suyo.
    assert get_harness() is get_harness()


def test_cifra_inventada_cero_cuenta_como_inventada():
    """0 es falsy: si se cuenta por verdad, una fabricacion de 0 pasa por buena."""
    un = [
        {"id": "u1", "unanswerable": True, "abstained": True, "fabricated_value": "0"},
        {"id": "u2", "unanswerable": True, "abstained": True, "fabricated_value": None},
        {"id": "u3", "unanswerable": True, "abstained": False, "fabricated_value": None},
    ]
    for r in un:
        r.update(judge=None, judge_error=None, difficulty="facil", cite_precision=0.0,
                 cite_coverage=0.0, answer_has_cite=False, answer="x", answer_cites=0,
                 turns=1, truncated=False, fallback=False, latency_s=1,
                 agent_usage={"total_tokens": 1, "calls": 1})
    agg = H.aggregate(un, turns=4, retries=1)
    assert agg["n_unanswerable"] == 3
    assert agg["n_fabricated"] == 1, agg["n_fabricated"]
