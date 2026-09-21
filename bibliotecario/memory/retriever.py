"""Retriever híbrido UNIFICADO: denso + keyword + evidencia de grafo en UNA sola ponderación.

Corrige el bug del origen (doble ponderación distinta tree 0.5/0.3/0.2 vs retriever 0.4/0.3/0.3):
aquí hay un único punto de fusión documentado: 0.5 denso + 0.3 keyword + 0.2 grafo.
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

import numpy as np

from bibliotecario.core import storage
from bibliotecario.core.embeddings import blob_to_vec, encode_one
from bibliotecario.knowledge import pearl as PEARL

W_DENSE, W_KEYWORD, W_GRAPH = 0.5, 0.3, 0.2


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-záéíóúñü]{4,}", text.lower())}


def search(query: str, top_k: int = 8) -> list[dict]:
    qvec = encode_one(query)
    qtok = _tokens(query)
    graph_docs: dict[int, float] = {}
    try:
        # Sin LLM: la búsqueda híbrida no debe consumir cuota (el ranking LLM vive en retrieve_evidence).
        for ev in PEARL.retrieve_evidence(query, top_m=6, use_llm=False):
            for d in ev["doc_ids"]:
                graph_docs[d] = max(graph_docs.get(d, 0.0), min(1.0, ev["score"] / 10.0))
    except Exception as e:
        logger.warning("Evidencia de grafo no disponible, sigo sin ella: %s", e)
    scored = []
    with storage.get_conn() as conn:
        rows = conn.execute(
            "SELECT c.doc_id, c.chunk_idx, c.text, c.embedding, d.title FROM chunks c "
            "JOIN documents d ON d.id=c.doc_id").fetchall()
    for r in rows:
        dense = float(np.dot(qvec, blob_to_vec(r["embedding"]))) if r["embedding"] else 0.0
        ct = _tokens(r["text"])
        kw = len(qtok & ct) / max(1, len(qtok))
        gr = graph_docs.get(r["doc_id"], 0.0)
        score = W_DENSE * dense + W_KEYWORD * kw + W_GRAPH * gr
        scored.append((score, r["doc_id"], r["chunk_idx"], r["title"], r["text"], dense, kw, gr))
    scored.sort(key=lambda x: -x[0])
    return [{"score": round(s, 3), "doc_id": d, "chunk": c, "title": t, "text": tx,
             "parts": {"dense": round(dn, 3), "keyword": round(k, 3), "graph": round(g, 3)}}
            for s, d, c, t, tx, dn, k, g in scored[:top_k]]
