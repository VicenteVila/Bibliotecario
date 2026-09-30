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


def test_search_expansion_vecinos(tmp_path, monkeypatch):
    """La expansión añade los chunks contiguos al hit principal, con score decaído."""
    from bibliotecario.memory import retriever as R
    db = tmp_path / "vecinos.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Doc Vecinos", "h1"))
        for i in range(5):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 if i == 2 else 0.0
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, f"chunk numero {i} con contexto", vec.tobytes()))
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])

    base = R.search("q", top_k=1)
    assert base[0]["chunk"] == 2 and "neighbour_of" not in base[0]
    hits = R.search_with_neighbours("q", top_k=1, window=1)
    assert {1, 2, 3} <= {h["chunk"] for h in hits}
    assert all(h["score"] <= base[0]["score"] for h in hits)
    assert any("neighbour_of" in h for h in hits)


def test_search_sin_expansion_si_window_cero(tmp_path, monkeypatch):
    from bibliotecario.memory import retriever as R
    db = tmp_path / "vecinos0.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Vacio", "h2"))
    assert R.search_with_neighbours("q", top_k=3, window=0) == []


def test_deep_sweep_cubre_apendice(tmp_path, monkeypatch):
    """El detalle específico está en un apéndice que el ranking no alcanza: el barrido debe verlo."""
    from bibliotecario.agent import tools as T
    db = tmp_path / "sweep.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Con Apendice", "h9"))
        for i in range(40):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 - i * 0.02  # el último chunk es el peor por denso
            txt = "texto general sin relacion " * 20
            if i == 30:
                # apéndice: sin solapamiento léxico con la query, solo alcanzable por cobertura
                txt = "Appendix: en igualdad de metricas se conserva la primera opcion registrada"
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, txt, vec.tobytes()))
    import bibliotecario.memory.retriever as R
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])

    top6 = {h["chunk"] for h in R.search("desempate", top_k=6)}
    found = {c["chunk"] for d in T.deep_sweep("desempate", per_doc=4)["docs"] for c in d["chunks"]}
    assert 30 not in top6  # el top-6 por relevancia no lo alcanza
    assert 30 in found  # el barrido con cobertura de documento sí


def test_deep_sweep_ordena_por_indice(tmp_path, monkeypatch):
    """El barrido ordena por índice para que el agente lea contexto contiguo."""
    import bibliotecario.memory.retriever as R
    from bibliotecario.agent import tools as T
    db = tmp_path / "orden.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Orden", "h10"))
        for i in range(12):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 - i * 0.05
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, f"chunk {i}", vec.tobytes()))
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])
    idx = [c["chunk"] for c in T.deep_sweep("chunk", per_doc=3)["docs"][0]["chunks"]]
    assert idx == sorted(idx)


@pytest.mark.parametrize("qid,gold_chunks", [
    ("wiki-2", {(5, 57)}),
    ("tce-3", {(3, 40)}),
    ("tce-2", {(3, 39), (3, 40)}),
    ("reas-3", {(4, 10), (4, 55), (4, 58)}),
])
def test_gold_evidence_alcanzable_en_cierre(qid, gold_chunks, monkeypatch):
    """Regresión: el cierre (top-8 + barrido) debe poder alcanzar la evidencia que
    responde a cada pregunta difícil del golden set.

    Sin esto el agente cerraba sin haber visto nunca el chunk con la respuesta
    (p. ej. el apéndice de WikiSkill, c57) y por eso fallaba aunque la cita era
    correcta. Sets de chunks porque varias respuestas son válidas por pregunta.
    """
    import json
    from pathlib import Path

    from bibliotecario.agent.tools import deep_sweep, search_papers

    root = Path(__file__).resolve().parents[1]
    db, ev = root / "data" / "bibliotecario.db", root / "evals" / "golden_qa.jsonl"
    if not ev.exists() or not db.exists():
        pytest.skip("requiere corpus ingerido")
    # db_path puede quedar monkeypatcheado por otros tests del módulo
    monkeypatch.setattr(storage, "db_path", lambda: db)
    q = next(json.loads(l)["question"] for l in ev.read_text().splitlines()
             if l.strip() and json.loads(l)["id"] == qid)
    base = {(h["doc_id"], h["chunk"]) for h in search_papers(q, top_k=8)["hits"]}
    sweep = {(d["doc_id"], c["chunk"]) for d in deep_sweep(q)["docs"] for c in d["chunks"]}
    assert gold_chunks & (base | sweep), f"{qid}: evidencia gold inalcanzable"


@pytest.mark.parametrize("qid,needle", [
    ("wiki-2", "5 failing traces"),   # el tope exacto, al final del c57
    ("tce-3", "earliest candidate"),  # la regla de desempate, a mitad del c40
])
def test_cierre_incluye_el_dato_literal(qid, needle, monkeypatch):
    """El cierre debe llevar el texto ÍNTEGRO del chunk con el dato.

    Regresión: se truncaba el chunk a 900 chars y la respuesta ("5 failing traces"),
    que está en la segunda mitad del c57) quedaba cortada. Con el texto completo el
    agente puede copiar la cifra literal en vez de inventarla.
    """
    import json
    from pathlib import Path

    from bibliotecario.agent.loop import _deep_evidence

    root = Path(__file__).resolve().parents[1]
    db, ev = root / "data" / "bibliotecario.db", root / "evals" / "golden_qa.jsonl"
    if not ev.exists() or not db.exists():
        pytest.skip("requiere corpus ingerido")
    monkeypatch.setattr(storage, "db_path", lambda: db)
    q = next(json.loads(l)["question"] for l in ev.read_text().splitlines()
             if l.strip() and json.loads(l)["id"] == qid)
    assert needle in _deep_evidence(q)
