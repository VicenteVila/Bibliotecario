"""Tests del juez: parsing estricto y métricas del harness. No gastan API.

El smoke test con llamadas reales (evals/judge_smoke.py) es un pre-flight
manual: verifica que el juez discrimina. Esto verifica la maquinaria que hay
alrededor, que sí se puede testear sin red.
"""
import json

import pytest

from evals.eval_end2end import citation_metrics, gold_docs
from evals.judge import _parse


@pytest.mark.parametrize("raw,expected", [
    ('{"score": 4, "verdict": "ok"}', 4),
    ('```json\n{"score": 2, "verdict": "mal"}\n```', 2),          # vallas markdown
    ('Aqui va mi respuesta: {"score": 5, "verdict": "bien"} fin', 5),  # JSON embebido
    ('{"verdict": "sin score"}', None),                          # falta score
    ('{"score": 9, "verdict": "fuera de rango"}', None),          # score invalido
    ('{"score": 0, "verdict": "cero"}', None),                    # fuera de 1..5
    ('no soy json en absoluto', None),
    ('', None),
    (None, None),
])
def test_parse_estricto(raw, expected):
    got = _parse(raw)
    if expected is None:
        assert got is None or got["score"] == expected
    else:
        assert got is not None and got["score"] == expected


def test_parse_no_acepta_json_con_score_fuera_de_rango():
    """Un 9 no puede colarse como score: el harness lo trataria como nota valida."""
    assert _parse('{"score": 9, "verdict": "x"}') is None


def test_gold_docs_acepta_lista_o_doc_id():
    assert gold_docs({"doc_id": 3}) == [3]
    assert gold_docs({"doc_id": 4, "answerable_docs": [4, 5]}) == [4, 5]


def test_citation_metrics_multi_paper_no_tiene_techo_de_0_5():
    """reas-3 necesita ReASearch y WikiSkill; antes su provenance topaba en 0.5
    y eso se leia como un fallo del agente."""
    q = {"doc_id": 4, "answerable_docs": [4, 5]}
    m = citation_metrics(q, "segun [4:10] y [5:57]", [])
    assert m["cite_precision"] == 1.0, "si solo cita papers correctos, precision = 1"
    assert m["cite_coverage"] == 1.0, "si cita los dos papers, cobertura = 1"
    assert m["stray_docs"] == 0


def test_citation_metrics_detecta_papers_sin_relacion():
    """Si cita un paper que no toca la pregunta, la precision baja pero la cobertura
    no: son dos cosas distintas y hay que poder verlas por separado."""
    q = {"doc_id": 4, "answerable_docs": [4, 5]}
    m = citation_metrics(q, "segun [4:10] y [3:2]", [])
    assert m["cite_precision"] == 0.5  # 1 de 2 docs citados es del gold
    assert m["cite_coverage"] == 0.5  # solo cubre 1 de los 2 papers que pide
    assert m["stray_docs"] == 1


def test_citation_metrics_sin_citas():
    q = {"doc_id": 4}
    m = citation_metrics(q, "sin citas", [])
    assert m["cite_precision"] == 0.0
    assert m["cite_coverage"] == 0.0


def test_golden_tiene_answerable_docs_en_todas_las_filas():
    """Si una fila nueva no declara sus papers, la métrica vuelve a usar doc_id y
    las preguntas multi-paper vuelven a estar condenadas."""
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "evals" / "golden_qa.jsonl"
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows, "golden vacio"
    for r in rows:
        assert r.get("answerable_docs"), f"{r['id']} sin answerable_docs"
        assert r.get("doc_id") in r["answerable_docs"], f"{r['id']}: doc_id no esta en la lista"