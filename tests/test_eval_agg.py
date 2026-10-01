"""Tests del agregado y del reparto de las preguntas no respondibles.

Este harness ya cometió dos veces el mismo tipo de bug: descartar de la media
lo que no se pudo medir (judges no parseables) y mezclar poblaciones
incomparables (provenance contra un doc_id en preguntas multi-paper). Aquí se
ciñan las dos cosas.
"""
import json

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
                        lambda q, max_turns=4: {"answer": "no consta en el corpus",
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