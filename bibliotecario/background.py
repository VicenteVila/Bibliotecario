"""Gestor de evolución en background: consolida memoria + refina grafo desde lessons.

Ciclo: MT.consolidate() → refiner desde lessons recientes (fallidas=what_failed,
exitosas=what_worked) → reporte. Sin LLM degrada a solo-consolidar.
"""
from __future__ import annotations

import logging

from bibliotecario.core import storage
from bibliotecario.knowledge import refiner as REF
from bibliotecario.memory import memory_tree as MT

logger = logging.getLogger(__name__)


def run_cycle() -> dict:
    report: dict = {}
    report["consolidate"] = MT.consolidate()
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT what_worked, what_failed FROM lessons ORDER BY id DESC LIMIT 10").fetchall()
    failed = [r["what_failed"] for r in rows if r["what_failed"]]
    succeeded = [r["what_worked"] for r in rows if r["what_worked"]]
    report["refine"] = REF.refine_from_trajectories(failed, succeeded, scope="background")
    logger.info("Background cycle: %s", report)
    return report
