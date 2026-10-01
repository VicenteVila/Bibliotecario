"""Regresion del truncado del barrido profundo (`_deep_evidence`).

El agente solo ve lo que le llega. `_deep_evidence` corta el resultado de
`deep_sweep` a `n_docs` papers. Ese recorte era exclusivo: el paper gold de
`wiki-b4` (doc 5, el que la propia pregunta nombra) caia en 4º lugar del ranking
y sus chunks 57-59 no llegaban nunca al cierre. Con 58k caracteres de evidencia
y ninguno de los tres chunks que responden, el judge daba un 2 con la evidencia
"completa".

Aqui se fija el contrato, no el numero: el barrido debe dejar pasar al paper que
la pregunta nombra.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bibliotecario.agent import loop as LOOP


def _barrido_falso(monkeypatch, docs):
    """Sustituye deep_sweep por uno fijo para no depender de la DB ni de la red."""
    monkeypatch.setitem(LOOP.TOOLS["deep_sweep"], "fn",
                        lambda question, per_doc=4: {"docs": docs})


def _doc(doc_id, chunks, score=0.3):
    return {"doc_id": doc_id, "title": f"Paper {doc_id}",
            "chunks": [{"chunk": c, "score": score, "text": f"texto {doc_id}:{c}"}
                       for c in chunks]}


def test_n_docs_por_defecto_no_recorta_en_exclusiva(monkeypatch):
    """4 papers es el default: con 2 el gold en 4º lugar se quedaba fuera."""
    assert LOOP._deep_evidence.__defaults__[1] == 4


def test_el_paper_que_la_pregunta_nombra_llega_al_cierre(monkeypatch):
    """El caso real de wiki-b4: doc gold en 4º puesto del ranking."""
    docs = [_doc(4, [30]), _doc(2, [29]), _doc(3, [40]), _doc(5, [57, 58, 59])]
    _barrido_falso(monkeypatch, docs)
    ev = LOOP._deep_evidence("¿que procedure estadistico usa WikiSkill?")
    for cc in (57, 58, 59):
        assert f"[5:{cc}]" in ev, f"el chunk gold 5:{cc} no llego al cierre"
    assert "[5:57]" in ev and "texto 5:57" in ev


def test_el_recorte_sigue_existiendo(monkeypatch):
    """n_docs explicito manda: no es que se haya eliminado el limite."""
    docs = [_doc(1, [0]), _doc(2, [0]), _doc(3, [0]), _doc(4, [0]), _doc(5, [0])]
    _barrido_falso(monkeypatch, docs)
    ev = LOOP._deep_evidence("q", n_docs=2)
    assert "[1:0]" in ev and "[5:0]" not in ev


def test_evidencia_degrada_sin_reventar(monkeypatch):
    """Si el barrido falla, el cierre sigue con lo que tenga."""

    def revienta(question, per_doc=4):
        raise RuntimeError("sin DB")

    monkeypatch.setitem(LOOP.TOOLS["deep_sweep"], "fn", revienta)
    assert LOOP._deep_evidence("q") == ""


def test_sin_documentos_devuelve_vacio(monkeypatch):
    _barrido_falso(monkeypatch, [])
    assert LOOP._deep_evidence("q") == ""