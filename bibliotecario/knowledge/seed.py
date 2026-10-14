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
    # --- Ampliación 2026-10-14: los 14 papers del corpus ingerido ---
    # Cada procedimiento fue extraído del texto del paper y verificado en el
    # chunk indicado en CONOCIMIENTO.md. NO se inventó ninguno.
    # Los 4 papers restantes (Harness Engineering, Beyond the Model,
    # Agent Plasticity, An Empirical Study) son de MEDICIÓN, no de método:
    # no tienen grafo procedural y se declaran como tale en CONOCIMIENTO.md.
    "MetaSkill": {
        "doc": "Learning Meta-Skills for Agent Harness Design",
        "procedures": [
            ("build harness", "triggers", "target execution"),
            ("review execution feedback", "triggers", "update skill bank"),
            ("add meta-skill", "alternative_to", "revise meta-skill"),
            ("freeze skill bank", "triggers", "test-time construction"),
            ("BM25 retrieval", "alternative_to", "full-bank selection"),
        ],
    },
    "Mixture of Self-Improving Branches": {
        "doc": "Mixture of Self-Improving Branches",
        "procedures": [
            ("branch-local proposal", "triggers", "candidate evaluation"),
            ("coverage vote", "triggers", "development subset pruning"),
            ("prune development subsets", "triggers", "update proposal guidance"),
            ("update proposal guidance", "triggers", "next harness proposal"),
            ("select branch heads", "triggers", "build router"),
            ("evolving development subsets", "alternative_to", "fixed development set"),
        ],
    },
    "HARDE": {
        "doc": "HARDE: Optimizing Agent Harnesses",
        "procedures": [
            ("trigger module", "triggers", "monitor invocation"),
            ("isolated module probing", "triggers", "optimization guide"),
            ("optimization guide", "triggers", "guided optimization"),
            ("guided optimization", "refines", "iterative harness search"),
            ("propose one-module revision", "triggers", "evaluate updated harness"),
            ("guide reuse", "alternative_to", "per-setting probing"),
        ],
    },
    "JAZ": {
        "doc": "Harness as a Language",
        "procedures": [
            ("invoke agent loop", "generalizes", "codeact agent loop"),
            ("context window warning", "triggers", "tail recursive delegation"),
            ("tail recursive delegation", "generalizes", "context compaction"),
            ("construct solver inputs", "triggers", "run solver on task"),
            ("run solver on task", "triggers", "inspect task results"),
            ("continual self improvement", "alternative_to", "ace self improvement loop"),
        ],
    },
    "Harness-of-Harness": {
        "doc": "Harness-of-Harness: Multi-Day",
        "procedures": [
            ("project planning", "triggers", "artifact development"),
            ("artifact development", "triggers", "independent quality assurance"),
            ("independent quality assurance", "triggers", "project planning"),
            ("shift-left testing", "refines", "artifact development"),
        ],
    },
    "HarnessDev": {
        "doc": "HarnessDev: Can LLMs Create",
        "procedures": [
            ("harness creation", "triggers", "harness evolution"),
            ("edit harness", "triggers", "run development cases"),
            ("run development cases", "triggers", "inspect feedback"),
            ("inspect feedback", "triggers", "edit harness"),
            ("probe evaluation", "alternative_to", "full evaluation pair"),
        ],
    },
    "Malena": {
        "doc": "How Much of a Harness Does a Strong Agent Need",
        "procedures": [
            ("coding agent session", "triggers", "autonomous search"),
            ("single long session", "generalizes", "oneshot iteration"),
            ("malena session", "alternative_to", "harness search orchestration"),
            ("malena session", "alternative_to", "multi-agent orchestration"),
            ("general pipeline", "triggers", "code patch search"),
        ],
    },
    "Agent as Its Own Optimizer": {
        "doc": "Self-Evolving Harness on Multiple Tasks",
        "procedures": [
            ("solver rollout", "triggers", "proposer update"),
            ("proposer update", "triggers", "engineering check"),
            ("engineering check", "triggers", "repair session"),
            ("multi-task pretraining", "triggers", "continual training"),
            ("edit budget annealing", "refines", "proposer update"),
        ],
    },
    "SoL-Pi": {
        "doc": "SoL-Pi: Recursively Scaling Auto-Research Loops",
        "procedures": [
            ("trajectory map reduce analysis", "triggers", "mechanism proposal"),
            ("mechanism proposal", "triggers", "candidate implementation"),
            ("candidate implementation", "triggers", "independent review"),
            ("failed review", "triggers", "candidate revision"),
            ("capability and efficiency gates", "triggers", "nondominated candidate retention"),
            ("cost gate", "triggers", "native compaction"),
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
