"""Registro procedimental: tripletas (procedure, relation, procedure) sobre el grafo unificado."""
from __future__ import annotations

from bibliotecario.knowledge import graph as G

RELATIONS = ("depends_on", "alternative_to", "refines", "generalizes", "conflicts_with",
             "triggers", "produces", "requires", "evaluates", "implements")


def register_procedure(label: str, technique: str | None = None, doc_id: int | None = None,
                       description: str = "") -> int:
    meta = {"description": description}
    if technique:
        meta["technique"] = technique
    if doc_id:
        meta["doc_id"] = doc_id
    pid = G.upsert_node("procedure", label, meta)
    if technique:
        tid = G.upsert_node("technique", technique, {"doc_id": doc_id} if doc_id else {})
        G.add_edge(pid, tid, "implements", "procedural")
    return pid


def link(src_label: str, relation: str, dst_label: str, weight: float = 1.0) -> int:
    assert relation in RELATIONS, relation
    src = G.upsert_node("procedure", src_label)
    dst = G.upsert_node("procedure", dst_label)
    return G.add_edge(src, dst, relation, "procedural", weight=weight)


def list_procedures(technique: str | None = None) -> list[G.Node]:
    procs = G.find_nodes("", kind="procedure", limit=500)
    if technique:
        return [p for p in procs if p.metadata.get("technique") == technique]
    return procs
