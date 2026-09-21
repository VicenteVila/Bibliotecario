import numpy as np
import pytest

from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import pearl as PEARL
from bibliotecario.knowledge import procedural as P
from bibliotecario.memory import memory_tree as MT


@pytest.fixture(autouse=True)
def _tmpdb(tmp_path, monkeypatch):
    db = tmp_path / "g.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    return db


def test_upsert_node_idempotente():
    a = G.upsert_node("technique", "Task-CoEvolve")
    b = G.upsert_node("technique", "Task-CoEvolve")
    assert a == b
    assert G.find_nodes("CoEvolve")[0].label == "Task-CoEvolve"


def test_add_edge_idempotente_y_vecinos():
    s = G.upsert_node("procedure", "variance-weighted sampling")
    d = G.upsert_node("procedure", "full-set estimation")
    e1 = G.add_edge(s, d, "triggers", "procedural")
    e2 = G.add_edge(s, d, "triggers", "procedural", weight=0.7)
    assert e1 == e2
    neigh = G.neighbors(s)
    assert len(neigh) == 1 and neigh[0][1].label == "full-set estimation"


def test_procedural_registry():
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve")
    P.link("variance-weighted sampling", "triggers", "Hájek estimation")
    procs = P.list_procedures(technique="Task-CoEvolve")
    assert any(p.label == "Hájek estimation" for p in procs)
    with pytest.raises(AssertionError):
        P.link("a", "relacion_invalida", "b")


def test_pearl_pipeline_sin_llm(monkeypatch):
    monkeypatch.setattr(PEARL, "generate", lambda *a, **k: "")
    P.register_procedure("variance-weighted sampling", technique="Task-CoEvolve", doc_id=3)
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve", doc_id=3)
    P.link("variance-weighted sampling", "triggers", "Hájek estimation")
    ev = PEARL.retrieve_evidence("variance-weighted sampling estimation")
    assert ev and ev[0]["score"] == 1.0
    assert ev[0]["doc_ids"] == [3]
    assert any(s["kind"] == "procedure" for s in ev[0]["steps"])


def test_memory_tree_recall_y_consolidate():
    rng = np.random.RandomState(0)
    v1 = rng.rand(8).astype("float32"); v1 /= np.linalg.norm(v1)
    v2 = rng.rand(8).astype("float32"); v2 /= np.linalg.norm(v2)
    MT.add("lección sobre sampling", v1, level="L1")
    MT.add("ruido ortogonal", v2)
    hits = MT.recall(v1, top_k=2)
    assert hits[0]["content"] == "lección sobre sampling"
    rep = MT.consolidate()
    assert rep["forgotten"] == 0
