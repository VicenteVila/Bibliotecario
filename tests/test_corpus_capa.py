"""Capa de corpus: etiqueta en la ingesta + filtro de retrieval por BIBLIOTECARIO_CAPAS."""
from __future__ import annotations

import numpy as np
import pytest

from bibliotecario.core import storage
from bibliotecario.ingest import base, pipeline


def _doc(text=None, title="Doc"):
    # texto único por defecto: store() deduplica por hash y el segundo store
    # con el mismo texto devuelve el primer doc_id (su capa, no la nueva).
    return base.Document(source="f", source_type="txt", title=title,
                         text=text or f"{title} contenido de prueba " * 100)


def _capa(conn, doc_id):
    return conn.execute("SELECT corpus_capa FROM documents WHERE id=?", (doc_id,)).fetchone()["corpus_capa"]


def test_store_escribe_capa_y_valida(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "db_path", lambda: tmp_path / "t.db")
    storage.init_db(tmp_path / "t.db")
    monkeypatch.setattr(pipeline, "encode", lambda c: np.zeros((len(c), 4), dtype="float32"))

    r = pipeline.store(_doc(title="Por defecto"))
    with storage.get_conn() as conn:
        assert _capa(conn, r.doc_id) == "extendido"

    r = pipeline.store(_doc(title="De evaluacion"), capa="evaluacion")
    with storage.get_conn() as conn:
        assert _capa(conn, r.doc_id) == "evaluacion"

    # multivalor: los cinco fundacionales son también diana de preguntas
    r = pipeline.store(_doc(title="Fundacional"), capa="fundacional,evaluacion")
    with storage.get_conn() as conn:
        assert _capa(conn, r.doc_id) == "fundacional,evaluacion"

    with pytest.raises(ValueError, match="capa desconocida"):
        pipeline.store(_doc(title="Typo"), capa="evaluacioon")


def test_duplicado_no_reetiqueta_capa(tmp_path, monkeypatch):
    """El dedup por hash devuelve temprano: re-ingerir no cambia la capa."""
    monkeypatch.setattr(storage, "db_path", lambda: tmp_path / "t.db")
    storage.init_db(tmp_path / "t.db")
    monkeypatch.setattr(pipeline, "encode", lambda c: np.zeros((len(c), 4), dtype="float32"))
    doc = _doc(title="Congelado")
    r1 = pipeline.store(doc, capa="fundacional,evaluacion")
    pipeline.store(doc, capa="extendido")
    with storage.get_conn() as conn:
        assert _capa(conn, r1.doc_id) == "fundacional,evaluacion"


def test_ingest_dir_propaga_capa(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "db_path", lambda: tmp_path / "dir.db")
    storage.init_db(tmp_path / "dir.db")
    monkeypatch.setattr(pipeline, "encode", lambda c: np.zeros((len(c), 4), dtype="float32"))
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.txt").write_text("contenido alfa " * 200)
    r = pipeline.ingest_dir(str(inbox), capa="evaluacion")
    assert r["capa"] == "evaluacion" and r["ingested"] == 1
    with storage.get_conn() as conn:
        assert _capa(conn, 1) == "evaluacion"
    # sin capa: extendido, el comportamiento de siempre
    (inbox / "b.txt").write_text("contenido beta " * 200)
    assert pipeline.ingest_dir(str(inbox))["capa"] == "extendido"
    with storage.get_conn() as conn:
        assert _capa(conn, 2) == "extendido"
    with pytest.raises(ValueError):
        pipeline.ingest_dir(str(inbox), capa="nada")


def _dos_docs(tmp_path, monkeypatch, **env):
    """BD con doc 1 'fundacional,evaluacion' y doc 2 'extendido', embeddings simulados."""
    db = tmp_path / "retr.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn() as conn:
        for i, (title, capa) in enumerate(
                [("PEARL,Path-Entity Aligned Relational Learning", "fundacional,evaluacion"),
                 ("Paper extendido", "extendido")], start=1):
            conn.execute("INSERT INTO documents (path, title, paper_hash, corpus_capa) VALUES (?,?,?,?)",
                         (f"f{i}.pdf", title, f"h{i}", capa))
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (i, 0, f"texto del documento {i} sobre arneses de agentes", vec.tobytes()))
    monkeypatch.setattr("bibliotecario.memory.retriever.encode_one",
                        lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr("bibliotecario.memory.retriever.PEARL.retrieve_evidence",
                        lambda *a, **k: [])
    return db


def test_retriever_sin_filtro_ve_todo(tmp_path, monkeypatch):
    from bibliotecario.memory import retriever
    _dos_docs(tmp_path, monkeypatch)
    monkeypatch.delenv("BIBLIOTECARIO_CAPAS", raising=False)
    assert {h["doc_id"] for h in retriever.search("arneses de agentes", top_k=8)} == {1, 2}
    assert retriever.allowed_capas() is None


def test_retriever_filtra_por_capa(tmp_path, monkeypatch):
    from bibliotecario.memory import retriever
    _dos_docs(tmp_path, monkeypatch)
    monkeypatch.setenv("BIBLIOTECARIO_CAPAS", "evaluacion")
    assert retriever.allowed_capas() == {"evaluacion"}
    assert {h["doc_id"] for h in retriever.search("arneses de agentes", top_k=8)} == {1}

    # multivalor: 'extendido,evaluacion' también pasa el filtro de evaluacion
    with storage.get_conn() as conn:
        conn.execute("UPDATE documents SET corpus_capa='extendido,evaluacion' WHERE id=2")
    assert {h["doc_id"] for h in retriever.search("arneses de agentes", top_k=8)} == {1, 2}

    monkeypatch.setenv("BIBLIOTECARIO_CAPAS", "fundacional")
    assert {h["doc_id"] for h in retriever.search("arneses de agentes", top_k=8)} == {1}


def test_tools_evidencia_tambien_filtra(tmp_path, monkeypatch):
    """Sin esto el filtro solo valdría en search(): PEARL seguiría exponiendo lo prohibido."""
    from bibliotecario.agent import tools as T
    from bibliotecario.memory import retriever
    _dos_docs(tmp_path, monkeypatch)
    paths = [{"score": 9.0, "doc_ids": [2], "steps": [{"label": "a"}]},
             {"score": 8.0, "doc_ids": [1], "steps": [{"label": "b"}]}]
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: paths)
    monkeypatch.delenv("BIBLIOTECARIO_CAPAS", raising=False)
    assert T.retrieve_evidence("q")["paths"] == paths

    monkeypatch.setenv("BIBLIOTECARIO_CAPAS", "evaluacion")
    kept = T.retrieve_evidence("q")["paths"]
    assert [p["doc_ids"] for p in kept] == [[1]]
    assert retriever.docs_in_allowed_capa([2]) == []
    assert retriever.docs_in_allowed_capa([1, 2]) == [1]
