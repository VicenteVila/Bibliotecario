"""HITO12 §1.A — ventana de verificación por blueprint (enmienda 1, E12)."""
from __future__ import annotations

import numpy as np
import pytest

from bibliotecario.agent import tools as T
from bibliotecario.core import storage


@pytest.fixture
def doc_prueba(tmp_path, monkeypatch):
    # kw-only declarado: sin modelo de embeddings, la ranking es keyword
    def _boom(text):
        raise RuntimeError("sin embeddings en test")
    monkeypatch.setattr("bibliotecario.core.embeddings.encode_one", _boom)
    with storage.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
            ("p.pdf", "Doc Ventana", "hashv"))
        doc = cur.lastrowid
        for idx, text in enumerate((
                "Titulo Autores Sello",                      # chunk 0
                "stagnation advisory after flat evaluations",
                "search tree review branch concentration",
                "unrelated chess table results",
                "validation pre release rules",               # chunk 4
        )):
            conn.execute(
                "INSERT INTO chunks (doc_id, chunk_idx, text, embedding) "
                "VALUES (?,?,?,?)", (doc, idx, text, None))
    return doc


def test_chunk0_primero_y_formato(doc_prueba):
    _, win = T.fuente_verificable("TechX", "", doc_id=doc_prueba)
    assert win.startswith("[chunk 0] Titulo Autores Sello")
    assert "[chunk " in win


def test_citado_incluido_aunque_no_rankee(doc_prueba):
    bp = f"afirmación [doc:{doc_prueba}:4] puntero"
    _, win = T.fuente_verificable("TechX", bp, doc_id=doc_prueba)
    assert "[chunk 4] validation pre release rules" in win


def test_top10_kw_y_dedup(doc_prueba):
    bp = "stagnation advisory search tree validation"
    _, win = T.fuente_verificable("TechX", bp, doc_id=doc_prueba)
    assert "[chunk 1]" in win and "[chunk 2]" in win
    # el chunk 3 (sin términos) no rankea; dedup: chunk 0 no se repite
    assert win.count("[chunk 0]") == 1


def test_recorte_max_chars(doc_prueba):
    with storage.get_conn() as conn:
        for i in range(5, 40):
            conn.execute(
                "INSERT INTO chunks (doc_id, chunk_idx, text, embedding) "
                "VALUES (?,?,?,?)",
                (doc_prueba, i, "x" * 500, None))
    _, win = T.fuente_verificable("TechX", "stagnation advisory",
                                  doc_id=doc_prueba, max_chars=9000)
    assert len(win) <= 9000
    assert win.startswith("[chunk 0]")


def test_sin_documento_devuelve_vacio():
    assert T.fuente_verificable("TechQueNoExiste", "bp") == (None, "")


def test_encode_ok_sin_embeddings_en_chunks(doc_prueba, monkeypatch):
    monkeypatch.setattr("bibliotecario.core.embeddings.encode_one",
                        lambda q: np.zeros(3))
    _, win = T.fuente_verificable("TechX", "stagnation advisory",
                                  doc_id=doc_prueba)
    assert "[chunk 0]" in win
