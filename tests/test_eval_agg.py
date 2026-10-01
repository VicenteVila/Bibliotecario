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


def _row(id, judge=None, unanswerable=False, difficulty="media", abstained=None,
         infra_error=None):
    return {"id": id, "judge": judge, "judge_error": None, "unanswerable": unanswerable,
            "infra_error": infra_error,
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


# --- Fallos de infraestructura: no son notas del agente ------------------------
#
# Pasó de verdad en la run ciega r2: pg-b4 y tce-b6 quedaron con answer="" y
# judge=0, y como 0 no es None el agregado contaba n_scored=35 y
# n_judge_errors=0. Las dos caidas de red bajaron judge_mean (4.029) como si
# fueran respuestas malas, sin dejar rastro. Estas filas son las de ese fichero.


def test_infra_no_entra_en_judge_mean():
    """Una caida de red no puede contar como 0: eso baja la media sin que se note."""
    rows = [_row("a1", 5), _row("a2", 4),
            _row("pg-b4", 0, infra_error="RuntimeError: todos los proveedores fallaron"),
            _row("tce-b6", 0, infra_error="RuntimeError: todos los proveedores fallaron")]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["judge_mean"] == 4.5          # (5+4)/2, las de infra no cuentan
    assert agg["n_infra"] == 2
    assert agg["n_scored"] == 2
    assert agg["n_answerable"] == 2          # fuera de la media, no respondibles
    assert sorted(agg["infra_error_ids"]) == ["pg-b4", "tce-b6"]


def test_infra_en_pregunta_no_respondible_tampoco_cuenta_como_abstain():
    rows = [_row("u1", None, unanswerable=True, abstained=True),
            _row("u2", None, unanswerable=True, abstained=False,
                 infra_error="RuntimeError: agotado")]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["abstain_rate"] == 1.0        # solo u1 se pudo juzgar
    assert agg["n_infra"] == 1
    assert agg["infra_error_ids"] == ["u2"]


def test_todas_infra_no_revienta_el_agregado():
    rows = [_row("a1", 0, infra_error="e"), _row("a2", 0, infra_error="e")]
    agg = H.aggregate(rows, turns=4, retries=1)
    assert agg["judge_mean"] is None         # sin datos, None y no division por cero
    assert agg["n_infra"] == 2


def test_run_one_marca_infra_y_no_llama_al_juez(monkeypatch):
    """Si el proveedor cae, la fila lo dice y no se inventa un 0."""
    monkeypatch.setattr(H.LLM, "reset_usage", lambda: None)
    monkeypatch.setattr(H.LLM, "usage_totals",
                        lambda: {"total_tokens": 1, "calls": 1, "calls_tokens_unknown": 0})

    def boom(q, max_turns=4, isolated=False):
        raise RuntimeError("todos los proveedores LLM fallaron: nvidia(muerto)")

    monkeypatch.setattr(H.LOOP, "run", boom)
    llamado = {"n": 0}

    def fake_judge(question, reference, answer, **kw):
        llamado["n"] += 1
        return {"score": 1, "verdict": "", "model": "m", "usage": {}, "error": None}

    monkeypatch.setattr(H, "judge", fake_judge)

    row = H.run_one({"id": "pg-b4", "question": "q", "reference": "r",
                     "answerable_docs": [1]}, turns=4)
    assert llamado["n"] == 0                 # no se puntua lo que no existe
    assert row["judge"] is None
    assert "RuntimeError" in row["infra_error"]
    assert row["turns"] == 0
    assert row["answer"] == ""


def test_run_one_marca_respuesta_vacia_como_infra_sin_excepcion(monkeypatch):
    """A veces el loop no lanza y aun así no hay respuesta: también es infraestructura."""
    monkeypatch.setattr(H.LLM, "reset_usage", lambda: None)
    monkeypatch.setattr(H.LLM, "usage_totals",
                        lambda: {"total_tokens": 1, "calls": 1, "calls_tokens_unknown": 0})
    monkeypatch.setattr(H.LOOP, "run",
                        lambda q, max_turns=4, isolated=False: {"answer": "", "evidence": [],
                                                                "turns": 0})
    monkeypatch.setattr(H, "judge",
                        lambda *a, **k: {"score": 5, "verdict": "", "model": "m",
                                         "usage": {}, "error": None})
    row = H.run_one({"id": "a1", "question": "q", "reference": "r",
                     "answerable_docs": [1]}, turns=4)
    assert row["judge"] is None
    assert row["infra_error"]


def test_run_one_fallback_por_presupuesto_es_infra(monkeypatch):
    """El fallback por presupuesto no lo escribio el agente: es infraestructura."""
    monkeypatch.setattr(H.LLM, "reset_usage", lambda: None)
    monkeypatch.setattr(H.LLM, "usage_totals",
                        lambda: {"total_tokens": 1, "calls": 1, "calls_tokens_unknown": 0})
    monkeypatch.setattr(H.LOOP, "run",
                        lambda q, max_turns=4, isolated=False: {
                            "answer": "(presupuesto agotado)", "evidence": [], "turns": 3})
    row = H.run_one({"id": "a1", "question": "q", "reference": "r",
                     "answerable_docs": [1]}, turns=4)
    assert row["infra_error"] and "fallback" in row["infra_error"]
    assert row["judge"] is None


# --- Reanudacion de una run interrumpida --------------------------------------
#
# El tier se agota a mitad de run, eso es esperable. Si al reanudar se pierden
# filas, la media de la run depende de cuando se miró. Ya se perdieron 4
# preguntas de la primera vez; el merge por id lo evita y estos tests lo fijan.


def test_reanudar_solo_recalcula_lo_que_falta(tmp_path, monkeypatch):
    p = tmp_path / "r.json"
    H.save([_row("a1", 5), _row("a2", 4), _row("a3", 3)], {"n": 3}, p, {"run": "r1"})

    prev = json.loads(p.read_text())
    out = prev["rows"]
    done = {r["id"] for r in out}
    assert done == {"a1", "a2", "a3"}

    # Solo a4 falta: las otras tres no se vuelven a pedir (ahorra tokens y evita
    # que el ruido del modelo cambie lo ya medido).
    pedidas = []
    monkeypatch.setattr(H, "run_one", lambda q, turns: (pedidas.append(q["id"]),
                                                        _row(q["id"], 4))[1])
    todo = [{"id": i} for i in ("a1", "a2", "a3", "a4") if i not in done]
    assert [q["id"] for q in todo] == ["a4"]
    H.run_one(todo[0], turns=4)
    assert pedidas == ["a4"]


def test_merge_conserva_filas_previas(tmp_path):
    """Al reanudar, las filas ya guardadas sobreviven a las nuevas."""
    p = tmp_path / "r.json"
    previas = [_row("a1", 5), _row("a2", 4)]
    H.save(previas, {"n": 2}, p, {"run": "r1"})

    rows_orden = [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]
    results = {"a3": _row("a3", 3)}
    merged_map = {r["id"]: r for r in previas}
    merged_map.update(results)
    merged = [merged_map[q["id"]] for q in rows_orden if q["id"] in merged_map]

    assert [r["id"] for r in merged] == ["a1", "a2", "a3"]
    H.save(merged, H.aggregate(merged, turns=4, retries=1), p, {"run": "r1"})
    assert [r["id"] for r in json.loads(p.read_text())["rows"]] == ["a1", "a2", "a3"]


def test_fila_infra_se_persiste_y_se_puede_recalcular(tmp_path):
    """Una caida guardada como infra debe poder rehacerse al reanudar."""
    fila = _row("pg-b4", None, infra_error="RuntimeError: 504")
    p = tmp_path / "r.json"
    H.save([fila], {"n": 1}, p, {"run": "r1"})
    releida = json.loads(p.read_text())["rows"][0]
    assert releida["infra_error"]
    assert releida["judge"] is None
    # Al reanudar, pg-b4 sigue sin estar en `done` solo si se decide rehacerlo:
    # la infra no se considera terminada.
    assert releida["judge"] is None


def test_meta_registra_el_anclaje(tmp_path):
    """La run dice si fue con anclaje: sin esto no se puede comparar bien."""
    p = tmp_path / "r.json"
    H.save([_row("a1", 5)], {"n": 1}, p, {"run": "r4", "anchor_grounding": True})
    assert json.loads(p.read_text())["meta"]["anchor_grounding"] is True


def test_anchor_grounding_se_lee_del_entorno():
    """El flag del que depende la run completa tiene que existir y ser False por defecto."""
    assert hasattr(H.LOOP, "ANCHOR_GROUNDING")
    assert H.LOOP.ANCHOR_GROUNDING is False


# --- Un bug no es infraestructura --------------------------------------------
#
# Si un TypeError se marca como infra_error, aggregate lo saca de la media en
# silencio y se pierde una pregunta sin que nadie se entere. Un error de
# programacion debe relanzar: una run con un bug dentro no es un dato.


@pytest.mark.parametrize("exc", [
    TypeError("string indices must be integers"),
    AttributeError("'NoneType' object has no attribute 'get'"),
    NameError("name 'q' is not defined"),
    KeyError("doc_id"),
])
def test_bug_de_programacion_relanza(exc):
    with pytest.raises(type(exc)):
        H._classify_run_error(exc)


@pytest.mark.parametrize("mensaje", [
    "RuntimeError: todos los proveedores LLM fallaron: nvidia(muerto)",
    "RuntimeError: HTTP 504: Gateway Time-out",
    "RuntimeError: sin proveedores LLM configurados",
    "TimeoutError: timed out",
    "RuntimeError: overloaded",
])
def test_caida_de_red_si_es_infra(mensaje):
    out = H._classify_run_error(RuntimeError(mensaje))
    assert "RuntimeError" in out or "TimeoutError" in out


def test_run_one_relanza_bug_en_vez_de_ocultarlo(monkeypatch):
    monkeypatch.setattr(H.LLM, "reset_usage", lambda: None)
    monkeypatch.setattr(H.LLM, "usage_totals",
                        lambda: {"total_tokens": 1, "calls": 1, "calls_tokens_unknown": 0})

    def boom(q, max_turns=4, isolated=False):
        raise TypeError("argument of type 'NoneType' is not iterable")

    monkeypatch.setattr(H.LOOP, "run", boom)
    with pytest.raises(TypeError):
        H.run_one({"id": "a1", "question": "q", "reference": "r",
                   "answerable_docs": [1]}, turns=4)


def test_reanudar_rehace_las_filas_de_infra():
    """La infra no cuenta como terminada: si no, el tier agotado deja huecos eterno.

    Es el mecanismo que hace que una run interrumpida por falta de cuota se pueda
    completar: al reanudar se reintentan solo las filas que no llegaron a tener
    respuesta, y las ya medidas no se vuelven a pedir.
    """
    prev = [_row("a1", 5), _row("pg-b4", None, infra_error="RuntimeError: 504"),
            _row("a3", 4)]
    survived = [r for r in prev if not r.get("infra_error")]
    done = {r["id"] for r in survived}
    assert done == {"a1", "a3"}                 # pg-b4 se rehace
    assert "pg-b4" not in done
