"""Upsert semántico de la ingesta: idempotencia, actualización de metadatos y reindexado.

Cubre las tres ramas de `pipeline.store()` (duplicado / metadatos / texto
nuevo para la misma clave), la preservación de `corpus_capa` y el guardia de
`paper_hash` UNIQUE.
"""
from __future__ import annotations

import json

import numpy as np

from bibliotecario.core import storage
from bibliotecario.ingest import base, pipeline


def _setup(tmp_path, monkeypatch, name="upsert.db"):
    db = tmp_path / name
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    monkeypatch.setattr(pipeline, "encode", lambda c: np.zeros((len(c), 4), dtype="float32"))
    return db


def _doc(text, title="Doc", source="doc.pdf", metadata=None):
    return base.Document(source=source, source_type="txt", title=title, text=text,
                         metadata=dict(metadata or {}))


def _row(db, doc_id):
    with storage.get_conn(db) as conn:
        return dict(conn.execute(
            "SELECT id, path, title, paper_hash, metadata, corpus_capa "
            "FROM documents WHERE id=?", (doc_id,)).fetchone())


def _nchunks(db, doc_id):
    with storage.get_conn(db) as conn:
        return conn.execute("SELECT COUNT(*) c FROM chunks WHERE doc_id=?",
                            (doc_id,)).fetchone()["c"]


def test_duplicado_puro_no_escribe_nada(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch)
    doc = _doc("texto de prueba " * 100, metadata={"citations": {}})
    r1 = pipeline.store(doc, capa="evaluacion")
    r2 = pipeline.store(doc, capa="extendido")  # capa distinta: no debe aplicarse
    assert r1.action == "insertado" and r2.action == "duplicado"
    assert r2.doc_id == r1.doc_id
    assert "duplicado" in r2.quality_alerts[0]
    assert r2.chunks == 0
    row = _row(db, r1.doc_id)
    assert row["corpus_capa"] == "evaluacion"  # un duplicado no reetiqueta


def test_metadatos_se_actualizan_sin_reindexar(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch)
    doc = _doc("un paper " * 100)
    r1 = pipeline.store(doc, capa="fundacional")
    n1 = _nchunks(db, r1.doc_id)

    doc2 = _doc("un paper " * 100, metadata={"year": 2026, "authors": ["Ada"]})
    r2 = pipeline.store(doc2, capa="extendido")
    assert r2.action == "metadatos actualizados"
    assert r2.doc_id == r1.doc_id and r2.chunks == 0
    assert _nchunks(db, r1.doc_id) == n1  # sin re-embeddings

    row = _row(db, r1.doc_id)
    meta = json.loads(row["metadata"])
    assert meta["year"] == 2026 and meta["authors"] == ["Ada"]
    assert row["corpus_capa"] == "fundacional"  # la capa no cambia en el UPDATE

    # idempotencia: la segunda pasada no vuelve a tocar la fila
    r3 = pipeline.store(doc2, capa="extendido")
    assert r3.action == "duplicado"


def test_valor_vacio_no_borra_metadatos(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch)
    r1 = pipeline.store(_doc("paginas " * 100, metadata={"pages": 21, "ocr_requested": False}))
    # re-ingesta sin los campos de extracción (p.ej. otro origen del mismo texto)
    r2 = pipeline.store(_doc("paginas " * 100, metadata={"pages": None}))
    assert r2.action == "duplicado" or r2.action == "metadatos actualizados"
    meta = json.loads(_row(db, r1.doc_id)["metadata"])
    assert meta.get("pages") == 21
    assert meta.get("ocr_requested") is False


def test_mismo_arxiv_texto_distinto_reemplaza_chunks(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch)
    ax = {"arxiv": {"id": "2601.00001", "version": "v1"}}
    r1 = pipeline.store(_doc("version uno " * 100, metadata=dict(ax)), capa="evaluacion")
    n1 = _nchunks(db, r1.doc_id)

    # v2 del mismo paper: distinta extracción (el hash cambia), misma clave
    r2 = pipeline.store(_doc("version dos, texto distinto " * 100,
                             metadata={"arxiv": {"id": "2601.00001", "version": "v2"}}),
                        capa="extendido")
    assert r2.action == "actualizado"
    assert r2.doc_id == r1.doc_id
    assert _nchunks(db, r1.doc_id) > 0
    with storage.get_conn(db) as conn:
        texts = " ".join(r["text"] for r in conn.execute(
            "SELECT text FROM chunks WHERE doc_id=?", (r1.doc_id,)))
        wiki = conn.execute("SELECT body FROM wiki_pages WHERE slug=?",
                            (f"raw-{r1.doc_id}",)).fetchone()
    assert "version dos" in texts and "version uno" not in texts
    assert n1 > 0 and wiki and "version dos" in wiki["body"]
    assert _row(db, r1.doc_id)["corpus_capa"] == "evaluacion"  # capa intacta
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"] == 1


def test_path_fallback_sin_arxiv(tmp_path, monkeypatch):
    db = _setup(tmp_path, monkeypatch)
    r1 = pipeline.store(_doc("texto a " * 100, source="mismo.pdf"))
    r2 = pipeline.store(_doc("texto b, distinto " * 100, source="mismo.pdf"))
    assert r2.action == "actualizado" and r2.doc_id == r1.doc_id
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"] == 1


def test_el_hash_manda_primero_no_se_reasigna(tmp_path, monkeypatch):
    """Contenido idéntico → su propia fila, aunque otra fila lleve su arXiv.

    El hash se consulta antes que la clave semántica: así `paper_hash` (UNIQUE)
    nunca se reasigna entre filas y dos documentos que compartan contenido no
    acaban chocando en el INSERT.
    """
    db = _setup(tmp_path, monkeypatch)
    r1 = pipeline.store(_doc("alpha " * 100, metadata={"arxiv": {"id": "2601.99999"}}))
    r2 = pipeline.store(_doc("beta " * 100, source="otro.pdf"))  # sin clave, hash propio
    # el texto es el de r2 pero la clave es la de r1 → manda el contenido
    r3 = pipeline.store(_doc("beta " * 100, source="tercero.pdf",
                             metadata={"arxiv": {"id": "2601.99999"}}))
    assert r3.ok and r3.doc_id == r2.doc_id
    assert r3.action == "metadatos actualizados"
    # r1 no toca su hash; r2 gana el arXiv como metadato
    assert _row(db, r1.doc_id)["paper_hash"] != _row(db, r2.doc_id)["paper_hash"]
    assert json.loads(_row(db, r2.doc_id)["metadata"])["arxiv"]["id"] == "2601.99999"
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"] == 2


def test_arxiv_sin_hash_ni_path_no_pisa_el_documento(tmp_path, monkeypatch):
    """Otra variante del mismo arXiv (traducción) = fila nueva, jamás un UPDATE.

    La traducción conserva el título original, así que ni arXiv ni título
    bastan: pisar el doc de `evaluacion` con el fichero en otro idioma sería
    un daño no recuperable (el duplicado, en cambio, se limpia).
    """
    db = _setup(tmp_path, monkeypatch)
    r1 = pipeline.store(_doc("original in english " * 100, source="original.pdf",
                             title="Harness as a Language",
                             metadata={"arxiv": {"id": "2609.26891"}}),
                        capa="evaluacion,extendido")
    r2 = pipeline.store(_doc("traduccion al castellano " * 100, source="traduccion.pdf",
                             title="Harness as a Language",  # mismo título
                             metadata={"arxiv": {"id": "2609.26891"}}))
    assert r2.action == "insertado" and r2.doc_id != r1.doc_id
    row1 = _row(db, r1.doc_id)
    assert "original in english" in _chunk_texts(db, r1.doc_id)
    assert row1["corpus_capa"] == "evaluacion,extendido"
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"] == 2

    # ...pero el mismo hash con otro path sí es el mismo documento (fichero copiado)
    r3 = pipeline.store(_doc("original in english " * 100, source="copia.pdf",
                             title="Harness as a Language",
                             metadata={"arxiv": {"id": "2609.26891"}}))
    assert r3.action in ("duplicado", "metadatos actualizados")
    assert r3.doc_id == r1.doc_id
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"] == 2


def _chunk_texts(db, doc_id):
    with storage.get_conn(db) as conn:
        return " ".join(r["text"] for r in conn.execute(
            "SELECT text FROM chunks WHERE doc_id=?", (doc_id,)))


def test_ingest_dir_resumen_de_acciones(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, name="dir.db")
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "a.txt").write_text("contenido alfa " * 200)
    (inbox / "b.txt").write_text("contenido beta " * 200)
    r1 = pipeline.ingest_dir(str(inbox))
    r2 = pipeline.ingest_dir(str(inbox))
    assert r1["acciones"] == {"insertado": 2}
    assert r2["acciones"] == {"duplicado": 2}
    assert [f["action"] for f in r2["files"]] == ["duplicado", "duplicado"]
