"""Grafo de conocimiento unificado y tipado en SQLite.

Nodos: entity | paper | technique | procedure.
Aristas: kind factual (what-is) o procedural (what-to-do), con relación tipada y peso.
Upserts propios (nada de INSERT OR REPLACE: preserva FKs e IDs estables).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from bibliotecario.core import storage

logger = logging.getLogger(__name__)

NODE_KINDS = ("entity", "paper", "technique", "procedure")
EDGE_KINDS = ("factual", "procedural")


@dataclass
class Node:
    id: int
    kind: str
    label: str
    metadata: dict


@dataclass
class Edge:
    id: int
    src: int
    dst: int
    relation: str
    kind: str
    weight: float
    metadata: dict


def _meta(row) -> dict:
    try:
        return json.loads(row["metadata"]) if row["metadata"] else {}
    except (ValueError, TypeError):
        return {}


def upsert_node(kind: str, label: str, metadata: dict | None = None) -> int:
    assert kind in NODE_KINDS, kind
    label = label.strip()[:300]
    meta = json.dumps(metadata or {}, ensure_ascii=False)
    with storage.get_conn() as conn:
        conn.execute(
            "INSERT INTO nodes (kind, label, metadata) VALUES (?,?,?) "
            "ON CONFLICT(kind, label) DO UPDATE SET metadata=CASE "
            "WHEN excluded.metadata IN ('{}','') THEN nodes.metadata "
            "ELSE excluded.metadata END",
            (kind, label, meta),
        )
        row = conn.execute("SELECT id FROM nodes WHERE kind=? AND label=?", (kind, label)).fetchone()
        return row["id"]


def get_node(node_id: int) -> Node | None:
    with storage.get_conn() as conn:
        row = conn.execute("SELECT * FROM nodes WHERE id=?", (node_id,)).fetchone()
    if not row:
        return None
    return Node(id=row["id"], kind=row["kind"], label=row["label"], metadata=_meta(row))


def find_nodes(query: str, kind: str | None = None, limit: int = 20) -> list[Node]:
    like = f"%{query}%"
    sql = "SELECT * FROM nodes WHERE label LIKE ?"
    args: list = [like]
    if kind:
        sql += " AND kind=?"
        args.append(kind)
    sql += " LIMIT ?"
    args.append(limit)
    with storage.get_conn() as conn:
        rows = conn.execute(sql, args).fetchall()
    return [Node(id=r["id"], kind=r["kind"], label=r["label"], metadata=_meta(r)) for r in rows]


def add_edge(src: int, dst: int, relation: str, kind: str,
             weight: float = 1.0, metadata: dict | None = None) -> int:
    assert kind in EDGE_KINDS, kind
    meta = json.dumps(metadata or {}, ensure_ascii=False)
    with storage.get_conn() as conn:
        conn.execute(
            "INSERT INTO edges (src, dst, relation, kind, weight, metadata) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(src, dst, relation, kind) DO UPDATE SET weight=excluded.weight, metadata=excluded.metadata",
            (src, dst, relation.strip()[:120], kind, weight, meta),
        )
        row = conn.execute(
            "SELECT id FROM edges WHERE src=? AND dst=? AND relation=? AND kind=?",
            (src, dst, relation.strip()[:120], kind)).fetchone()
        return row["id"]


def neighbors(node_id: int, kind: str | None = None, limit: int = 50) -> list[tuple[Edge, Node]]:
    sql = ("SELECT e.*, n.kind AS nkind, n.label AS nlabel, n.metadata AS nmeta FROM edges e "
           "JOIN nodes n ON n.id = CASE WHEN e.src=? THEN e.dst ELSE e.src END "
           "WHERE (e.src=? OR e.dst=?)")
    args: list = [node_id, node_id, node_id]
    if kind:
        sql += " AND e.kind=?"
        args.append(kind)
    sql += " ORDER BY e.weight DESC LIMIT ?"
    args.append(limit)
    out = []
    with storage.get_conn() as conn:
        for r in conn.execute(sql, args).fetchall():
            e = Edge(id=r["id"], src=r["src"], dst=r["dst"], relation=r["relation"],
                     kind=r["kind"], weight=r["weight"], metadata=_meta(r))
            other = r["dst"] if r["src"] == node_id else r["src"]
            out.append((e, Node(id=other, kind=r["nkind"], label=r["nlabel"],
                                metadata=json.loads(r["nmeta"]) if r["nmeta"] else {})))
    return out


def stats() -> dict:
    with storage.get_conn() as conn:
        n = conn.execute("SELECT COUNT(*) c FROM nodes").fetchone()["c"]
        e = conn.execute("SELECT COUNT(*) c FROM edges").fetchone()["c"]
        by_kind = dict(conn.execute("SELECT kind, COUNT(*) c FROM nodes GROUP BY kind").fetchall())
    return {"nodes": n, "edges": e, "by_kind": by_kind}
