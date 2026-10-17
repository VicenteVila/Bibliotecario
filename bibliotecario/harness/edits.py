"""Memoria durable de firmas de fallo (tabla harness_edits) — Hito 4.

Una firma es el mensaje de error de una run, normalizado. La meta-evolución
solo dispara cuando la misma firma aparece en MIN_RUNS runs distintas: una
vez es ruido, dos es patrón (K=2, decidido y declarado en evals/HITO4_PLAN.md
antes de existir este módulo).

La evolución vive aquí y no en la memoria de un proceso: `occurrences`
sobrevive a reinicios y `pattern` guarda el patrón con el que se creó el PF
para poder reconstruirlo (pfs.rehydrate_from_edits).
"""
from __future__ import annotations

import json
import logging
from typing import Any

from bibliotecario.core import storage

logger = logging.getLogger(__name__)

MIN_RUNS = 2  # K del plan: runs distintas con la misma firma antes de evolucionar
MAX_SIGNATURE = 120


def normalize_signature(msg: str) -> str:
    """Firma canónica de un fallo: espacios colapsados y tope de largo.

    El estado `last_error` del loop, la precondition del PF auto y la fila de
    harness_edits salen todos de aquí, así que coinciden literalmente.
    """
    return " ".join(str(msg).split())[:MAX_SIGNATURE]


def bump(signature: str) -> dict[str, Any]:
    """+1 ocurrencia de la firma; devuelve el estado tras el bump.

    El primer INSERT ya cuenta 1: el `+1` del ON CONFLICT solo corre en las
    repeticiones (si se insertara a 0, la primera run no contaría y K=2
    necesitaría tres).
    """
    with storage.get_conn() as conn:
        conn.execute(
            "INSERT INTO harness_edits (signature, occurrences) VALUES (?, 1) "
            "ON CONFLICT(signature) DO UPDATE SET occurrences = occurrences + 1",
            (signature,))
        row = conn.execute(
            "SELECT occurrences, evolved FROM harness_edits WHERE signature=?",
            (signature,)).fetchone()
        return {"occurrences": row["occurrences"], "evolved": bool(row["evolved"])}


def claim_evolution(signature: str) -> bool:
    """Reserva la evolución de una firma. Condicional para no duplicar con --workers.

    El primer hilo que pone evolved=1 con pf_name='pending' es el que
    evoluciona; los demás ven evolved=1 y se van. 'pending' es transitorio:
    si el proceso muere en medio, release_claim lo devuelve a 0.
    """
    with storage.get_conn() as conn:
        cur = conn.execute(
            "UPDATE harness_edits SET evolved=1, pf_name='pending', "
            "evolved_at=datetime('now') WHERE signature=? AND evolved=0",
            (signature,))
        return cur.rowcount == 1


def mark_evolved(signature: str, pf_name: str, pattern: dict[str, Any]) -> None:
    """Cierra la evolución con el PF creado y el patrón que lo originó."""
    with storage.get_conn() as conn:
        conn.execute(
            "UPDATE harness_edits SET pf_name=?, pattern=? WHERE signature=? AND evolved=1",
            (pf_name, json.dumps(pattern, ensure_ascii=False), signature))


def release_claim(signature: str) -> None:
    """Devuelve la firma a 'no evolucionada' si el PF no se pudo crear."""
    with storage.get_conn() as conn:
        conn.execute(
            "UPDATE harness_edits SET evolved=0, pf_name=NULL, evolved_at=NULL "
            "WHERE signature=? AND pf_name='pending'",
            (signature,))


def evolved_rows() -> list[dict[str, Any]]:
    """Firmas ya evolucionadas (sin pendientes) para rehidratar el registro."""
    with storage.get_conn() as conn:
        rows = conn.execute(
            "SELECT signature, pf_name, pattern FROM harness_edits "
            "WHERE evolved=1 AND pf_name IS NOT NULL AND pf_name!='pending' "
            "ORDER BY evolved_at, id").fetchall()
        return [dict(r) for r in rows]
