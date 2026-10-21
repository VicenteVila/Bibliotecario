"""Tokenizador compartido (core.tokens): siglas, cifras, stoplist y conteo exacto."""
from __future__ import annotations

import numpy as np

from bibliotecario.agent import tools
from bibliotecario.core import storage
from bibliotecario.core import tokens as TK
from bibliotecario.ingest import base, pipeline
from bibliotecario.knowledge import pearl as PEARL
from bibliotecario.memory import retriever


def test_siglas_cortas_y_cifras_entran():
    got = TK.tokens("Why does RAG break the OCR and the LLM? k=10 tau=5", drop_stop=False)
    assert {"why", "rag", "ocr", "llm", "10", "5"} <= got


def test_stoplist_quita_lo_vacio_y_conserva_lo_corto():
    frase = "why does the rag use OCR"
    con_stop = TK.tokens(frase)  # por defecto
    sin_stop = TK.tokens(frase, drop_stop=False)
    assert {"rag", "ocr", "use"} <= con_stop
    assert not (con_stop & {"why", "does", "the"})
    assert {"why", "does", "the"} <= sin_stop


def test_digitos_no_llevan_stoplist():
    got = TK.tokens("paso 3 y 10 con el")
    assert {"3", "10"} <= got
    assert "con" not in got and "el" not in got


def test_count_terms_es_token_exacto_no_subcadena():
    assert TK.count_terms("users use using user", ["use"]) == 1
    assert TK.count_terms("are care share are", ["are"]) == 2
    assert TK.count_terms("sin terminos", []) == 0


def test_retriever_usa_el_tokenizador_compartido():
    assert retriever._tokens("Why RAG k=10") == TK.tokens("Why RAG k=10")
    assert "rag" in retriever._tokens("Why RAG k=10")
    assert "10" in retriever._tokens("k=10")


def test_tools_y_semillas_pearl_lo_usan_tambien(monkeypatch):
    assert tools._toks("Why RAG") == TK.tokens("Why RAG")
    vistos = []
    monkeypatch.setattr(PEARL.G, "find_nodes",
                        lambda token, limit=3: vistos.append(token) or [])
    PEARL.seed_nodes("Failure? Use RAG")
    assert vistos == ["failure", "use", "rag"]  # sin '?' ni signos, en orden


def test_deep_sweep_cuenta_terminos_completos(tmp_path, monkeypatch):
    db = tmp_path / "kw.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    monkeypatch.setattr(pipeline, "encode",
                        lambda c: np.zeros((len(c), 4), dtype="float32"))
    doc = base.Document(source="f", source_type="txt", title="Doc",
                        text="users users users use users " + "relleno " * 100)
    r = pipeline.store(doc)
    got = tools._doc_keyword_chunks(r.doc_id, "use", per_doc=1)
    assert got and got[0]["kw"] == 1  # "users" no cuenta: es token exacto, no subcadena
