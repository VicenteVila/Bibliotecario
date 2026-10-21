"""Retriever híbrido UNIFICADO: denso + keyword + evidencia de grafo en UNA sola ponderación.

Corrige el bug del origen (doble ponderación distinta tree 0.5/0.3/0.2 vs retriever 0.4/0.3/0.3):
aquí hay un único punto de fusión documentado: 0.5 denso + 0.3 keyword + 0.2 grafo.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

import numpy as np

from bibliotecario.core import storage
from bibliotecario.core.embeddings import blob_to_vec, encode_one
from bibliotecario.core.tokens import tokens as _tokens
from bibliotecario.knowledge import pearl as PEARL

W_DENSE, W_KEYWORD, W_GRAPH = 0.5, 0.3, 0.2


def allowed_capas() -> set[str] | None:
    """Capas que el retrieval acepta, desde `BIBLIOTECARIO_CAPAS` (coma-separadas).

    Sin la variable → None → sin filtro: el corpus entero, el comportamiento
    de siempre. La variable es la única palanca (convención `BIBLIOTECARIO_*`
    igual que `BIBLIOTECARIO_DB`): el eval la fija con `--capas` y la registra
    en su meta, para que una run filtrada nunca se confunda con una sin filtrar.
    """
    raw = os.environ.get("BIBLIOTECARIO_CAPAS", "").strip()
    if not raw:
        return None
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _capa_ok(row_capa: str | None, allowed: set[str] | None) -> bool:
    """El documento pasa si alguna de sus capas está permitida (multivalor)."""
    if allowed is None:
        return True
    return bool({p.strip().lower() for p in (row_capa or "").split(",") if p.strip()} & allowed)


def docs_in_allowed_capa(doc_ids) -> list[int]:
    """Subconjunto de `doc_ids` que pasa el filtro de capas (sin filtro → todos).

    Lo usan también las tools que vienen del grafo (PEARL), cuyo filtro no se
    aplica en el WHERE de chunks: sin esto el filtro solo valdría para la
    búsqueda de texto y la evidencia de nodos seguiría exponiendo lo prohibido.
    """
    ids = [int(i) for i in doc_ids]
    allowed = allowed_capas()
    if allowed is None or not ids:
        return ids
    with storage.get_conn() as conn:
        rows = conn.execute(
            f"SELECT id, corpus_capa FROM documents WHERE id IN ({','.join('?' * len(ids))})",
            ids).fetchall()
    return [r["id"] for r in rows if _capa_ok(r["corpus_capa"], allowed)]


def search(query: str, top_k: int = 8) -> list[dict]:
    qvec = encode_one(query)
    qtok = _tokens(query)
    allowed = allowed_capas()
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
            "SELECT c.doc_id, c.chunk_idx, c.text, c.embedding, d.title, d.corpus_capa "
            "FROM chunks c JOIN documents d ON d.id=c.doc_id").fetchall()
    for r in rows:
        if not _capa_ok(r["corpus_capa"], allowed):
            continue
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


def search_with_neighbours(query: str, top_k: int = 6, window: int = 1) -> list[dict]:
    """Búsqueda + expansión a chunks vecinos.

    Los papers troceados pierden continuidad: el detalle que responde a la pregunta
    (un tope, una regla de desempate) suele estar en el chunk inmediatamente
    anterior o posterior al hit principal. Se añaden los vecinos con score
    decaído para que el agente los vea sin que dominen el ranking.
    """
    hits = search(query, top_k=top_k)
    if not hits or window <= 0:
        return hits
    seen = {(h["doc_id"], h["chunk"]) for h in hits}
    out = list(hits)
    try:
        with storage.get_conn() as conn:
            for h in hits:
                rows = conn.execute(
                    "SELECT c.chunk_idx, c.text, d.title FROM chunks c "
                    "JOIN documents d ON d.id=c.doc_id WHERE c.doc_id=? "
                    "AND c.chunk_idx BETWEEN ? AND ? ORDER BY c.chunk_idx",
                    (h["doc_id"], h["chunk"] - window, h["chunk"] + window)).fetchall()
                for r in rows:
                    key = (h["doc_id"], r["chunk_idx"])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({"score": round(h["score"] * 0.6, 3), "doc_id": h["doc_id"],
                                "chunk": r["chunk_idx"], "title": r["title"], "text": r["text"],
                                "neighbour_of": h["chunk"],
                                "parts": {"dense": 0, "keyword": 0, "graph": 0}})
    except Exception as e:  # degradación con gracia: la búsqueda base yaOk
        logger.warning("Expansión a vecinos no disponible: %s", str(e)[:120])
    return out
