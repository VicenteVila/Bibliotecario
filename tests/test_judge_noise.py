"""Fase 1: el muestreo de measure_judge_noise decide si la medicion vale.

Ya fallo una vez por dos motivos silenciosos (una caida de proveedor solo
existia en la r2, y las no respondibles se colaban por no tener nota), asi que
el clasificador queda fijado aqui.
"""
from pathlib import Path

import pytest

from evals.measure_judge_noise import _load_runs, pick_sample

EVALS = Path(__file__).resolve().parent.parent / "evals"


def _row(i, run, judge, answer="una respuesta con contenido", unanswerable=False):
    return {"id": i, "run": run, "judge": judge, "answer": answer,
            "unanswerable": unanswerable, "difficulty": "facil", "doc_id": 1}


def _rows(spec):
    out = {}
    for item in spec:
        i, r, judge, ans = item[:4]
        unans = item[4] if len(item) > 4 else False
        out[(r, i)] = _row(i, r, judge, ans, unans)
    return out


def test_caida_se_detecta_en_cualquier_run_no_solo_en_el_ultimo():
    """pg-b4 se rompio solo en la r2 y en la r3 contesto bien. Mirando la ultima
    no hay caida que ver, y el control se perdia justo cuando mas importaba."""
    rows = _rows([("pg-b4", 1, 5, "bien"), ("pg-b4", 2, 0, ""), ("pg-b4", 3, 5, "bien")])
    s = pick_sample(rows, [1, 2, 3], n=10)
    caidas = [x for x in s if x["categoria"] == "caida"]
    assert len(caidas) == 1
    assert caidas[0]["run"] == 2, caidas[0]


def test_caida_se_detecta_por_texto_vacio_y_no_por_la_nota():
    """Una respuesta vacia la nota 0. Si se clasificara por nota, caeria en
    'estable' (sd 0) y el control positivo se perderia."""
    rows = _rows([("pg-b4", 1, 0, ""), ("pg-b4", 2, 0, ""), ("pg-b4", 3, 0, "")])
    s = pick_sample(rows, [1, 2, 3], n=10)
    assert all(x["categoria"] == "caida" for x in s), s


def test_no_respondibles_quedan_fuera():
    """Las no respondibles las juzga judge_abstention, no judge: meterlas
    contamination el sd con otra metrica."""
    rows = _rows([("pearl-b8", 1, None, "", True), ("pearl-b8", 2, None, "", True),
                  ("wiki-b1", 1, 2, "x"), ("wiki-b1", 2, 2, "x"), ("wiki-b1", 3, 2, "x")])
    s = pick_sample(rows, [1, 2, 3], n=10)
    assert all(not x["id"].endswith("-b8") for x in s), s


def test_las_deterministas_que_fallan_tienen_prioridad():
    """wiki-b1=2,2,2 es el control con mas poder: si el juez es coherente tiene
    que dar 2 las tres veces. pearl-b1=5,5,5 casi no informa, asi que van detras."""
    spec = []
    for i, j in (("pearl-b1", 5), ("pearl-b2", 5), ("pearl-b3", 5),
                 ("wiki-b1", 2), ("wiki-b7", 2), ("tce-b7", 4)):
        spec += [(i, r, j, "x") for r in (1, 2, 3)]
    s = pick_sample(_rows(spec), [1, 2, 3], n=20)
    malas = [x["id"] for x in s if x["categoria"] == "determinista_mala"]
    assert set(malas) == {"wiki-b1", "wiki-b7", "tce-b7"}, malas


def test_el_muestreo_real_clasifica_lo_esperado():
    """Guardia contra un cambio de datos o de logica que rompa el muestreo."""
    golden, rows = _load_runs([1, 2, 3])
    if not rows:
        pytest.skip("sin runs en disco")
    s = pick_sample(rows, [1, 2, 3], n=20)
    cats = {x["categoria"] for x in s}
    assert {"caida", "determinista_mala", "inestable"} <= cats, cats
    assert len({x["key"] for x in s}) == len(s), "claves duplicadas"
    for x in s:
        # "unanswerable" solo esta presente en las filas no respondibles.
        assert not golden[x["id"]].get("unanswerable")
