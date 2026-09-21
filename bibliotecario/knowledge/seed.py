"""Bootstrap del grafo: nodos paper/technique/procedure desde los documentos ingeridos.

Idempotente (upserts): re-ejecutable sin duplicar. El refiner lo extiende después vía LLM.
"""
from __future__ import annotations

import logging

from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import procedural as P

logger = logging.getLogger(__name__)

TECHNIQUES = {
    "Task-CoEvolve": {
        "doc": "Task-CoEvolve",
        "procedures": [
            ("variance-weighted task selection", "triggers", "Hájek full-set estimation"),
            ("variance-weighted task selection", "triggers", "anchored difference estimation"),
            ("Hájek full-set estimation", "alternative_to", "anchored difference estimation"),
            ("anchored difference estimation", "triggers", "S-max final selection"),
            ("Hájek full-set estimation", "triggers", "S-max final selection"),
        ],
    },
    "PEARL": {
        "doc": "PEARL",
        "procedures": [
            ("contextual subgraph extraction", "triggers", "LLM-guided path retrieval"),
            ("LLM-guided path retrieval", "triggers", "dual-view subgraph contrast"),
            ("dual-view subgraph contrast", "triggers", "path-entity aggregation"),
            ("contextual subgraph extraction", "generalizes", "enclosing subgraph extraction"),
        ],
    },
    "WikiSkill": {
        "doc": "WikiSkill",
        "procedures": [
            ("skill-wiki co-evolution", "triggers", "stratified trace sampling"),
            ("stratified trace sampling", "triggers", "gating and rollback"),
            ("gating and rollback", "triggers", "skill transfer"),
        ],
    },
    "Procedural Graphs": {
        "doc": "Procedural",
        "procedures": [
            ("procedure-triplet extraction", "triggers", "failure-vs-success refiner"),
            ("failure-vs-success refiner", "triggers", "graph mutation"),
        ],
    },
    "ReASearch": {
        "doc": "Optimizer Is the Agent",
        "procedures": [
            ("tool-driven optimization loop", "triggers", "lessons persistence"),
            ("tool-driven optimization loop", "triggers", "context compaction"),
            ("tool-driven optimization loop", "triggers", "state re-emission"),
            ("state re-emission", "triggers", "stagnation advisory"),
            ("lessons persistence", "refines", "failure-vs-success refiner"),
        ],
    },
}


def seed() -> dict:
    with storage.get_conn() as conn:
        docs = conn.execute("SELECT id, title FROM documents").fetchall()
    n_procs = n_links = 0
    for tech, spec in TECHNIQUES.items():
        doc_id = next((d["id"] for d in docs if spec["doc"].lower() in (d["title"] or "").lower()), None)
        tid = G.upsert_node("technique", tech, {"doc_id": doc_id} if doc_id else {})
        if doc_id:
            with storage.get_conn() as conn:
                title = conn.execute("SELECT title FROM documents WHERE id=?", (doc_id,)).fetchone()["title"]
            pid = G.upsert_node("paper", title[:200], {"doc_id": doc_id})
            G.add_edge(pid, tid, "describes", "factual")
        for src, rel, dst in spec["procedures"]:
            P.register_procedure(src, technique=tech, doc_id=doc_id)
            P.register_procedure(dst, technique=tech if dst not in ("enclosing subgraph extraction",) else None,
                                 doc_id=doc_id)
            P.link(src, rel, dst)
            n_procs += 2
            n_links += 1
    stats = G.stats()
    logger.info("Seed grafo: %s", stats)
    return stats
