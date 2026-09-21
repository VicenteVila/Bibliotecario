"""MemoryTree H-Mem: niveles L0-L3 con olvido Ebbinghaus y refuerzo por acceso.

- L0: episódico reciente · L1: consolidado · L2: semántico · L3: núcleo persistente.
- strength decae exp(-Δt/TAU); cada acceso la refuerza +ETA (tope 1.0).
- consolidate(): aplica decaimiento y olvida strength < 0.05 (salvo L3).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime

import numpy as np

from bibliotecario.core import storage
from bibliotecario.core.embeddings import blob_to_vec, embed_blob

TAU_DAYS = 30.0
ETA = 0.5
FORGET_THRESHOLD = 0.05


def add(content: str, embedding: np.ndarray | None = None, level: str = "L0") -> int:
    assert level in ("L0", "L1", "L2", "L3"), level
    blob = embed_blob(embedding) if embedding is not None else None
    with storage.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO memory_items (level, content, embedding) VALUES (?,?,?)",
            (level, content, blob))
        return cur.lastrowid


def _utcnow() -> datetime:
    # SQLite datetime('now') es UTC naive; mantenemos naive-UTC en todo el módulo.
    return datetime.now(UTC).replace(tzinfo=None)


def _decay(strength: float, last_access: str) -> float:
    try:
        dt = (_utcnow() - datetime.fromisoformat(last_access)).total_seconds() / 86400
    except ValueError:
        return strength
    return strength * math.exp(-dt / TAU_DAYS)


def recall(query_vec: np.ndarray, top_k: int = 8, min_strength: float = 0.05) -> list[dict]:
    hits = []
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT id, level, content, embedding, strength, last_access FROM memory_items").fetchall()
        for r in rows:
            if r["embedding"] is None:
                continue
            s = _decay(r["strength"], r["last_access"])
            if s < min_strength and r["level"] != "L3":
                continue
            sim = float(np.dot(query_vec, blob_to_vec(r["embedding"])))
            hits.append((sim * (0.5 + 0.5 * s), r["id"], r["level"], r["content"], s))
    hits.sort(key=lambda x: -x[0])
    top = hits[:top_k]
    if top:  # refuerzo por acceso
        with storage.get_conn() as conn:
            for _, mid, _, _, s in top:
                conn.execute("UPDATE memory_items SET strength=MIN(1.0, ?+?), last_access=datetime('now') WHERE id=?",
                             (s, ETA, mid))
    return [{"id": mid, "level": lv, "content": c, "score": round(sc, 3)} for sc, mid, lv, c, _ in top]


def promote(item_id: int, level: str) -> None:
    assert level in ("L0", "L1", "L2", "L3"), level
    with storage.get_conn() as conn:
        conn.execute("UPDATE memory_items SET level=?, strength=1.0 WHERE id=?", (level, item_id))


def consolidate() -> dict:
    forgotten = 0
    with storage.get_conn() as conn:
        for r in conn.execute("SELECT id, level, strength, last_access FROM memory_items").fetchall():
            s = _decay(r["strength"], r["last_access"])
            if s < FORGET_THRESHOLD and r["level"] != "L3":
                conn.execute("DELETE FROM memory_items WHERE id=?", (r["id"],))
                forgotten += 1
            else:
                conn.execute("UPDATE memory_items SET strength=? WHERE id=?", (s, r["id"]))
    return {"forgotten": forgotten, "note": "L3 nunca se olvida"}
