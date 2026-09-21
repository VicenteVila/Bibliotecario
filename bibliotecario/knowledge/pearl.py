"""Motor PEARL a nivel de mecánica (sin GNNs): subgrafo contextual + LPRA + filtro dual-view.

1. Subgrafo contextual: unión de vecindarios BFS alrededor de nodos semilla.
2. LPRA: caminos candidatos por BFS, rankeados por relevancia semántica (Gemini; fallback por peso).
3. Dual-view: dos vistas estocásticas del subgrafo; se conserva el núcleo estable (intersección).
4. Agregación camino-entidad: evidencia rankeada para responder con citas.
"""
from __future__ import annotations

import itertools
import json
import logging
import random
from collections import deque

from bibliotecario.core import storage
from bibliotecario.core.llm import generate
from bibliotecario.knowledge import graph as G

logger = logging.getLogger(__name__)


def seed_nodes(query: str, limit: int = 8) -> list[G.Node]:
    seeds: list[G.Node] = []
    for token in [t for t in query.replace("?", " ").split() if len(t) > 3][:12]:
        seeds.extend(G.find_nodes(token, limit=3))
    seen, uniq = set(), []
    for n in seeds:
        if n.id not in seen:
            seen.add(n.id)
            uniq.append(n)
    return uniq[:limit]


def contextual_subgraph(seed_ids: list[int], depth: int = 2, max_nodes: int = 120) -> tuple[set[int], list[tuple]]:
    """BFS multi-origen; devuelve (nodos, aristas (src,dst,relation,kind,weight))."""
    nodes: set[int] = set(seed_ids)
    edges: list[tuple] = []
    frontier = deque((s, 0) for s in seed_ids)
    with storage.get_conn() as conn:
        while frontier and len(nodes) < max_nodes:
            cur, d = frontier.popleft()
            if d >= depth:
                continue
            for r in conn.execute("SELECT src,dst,relation,kind,weight FROM edges WHERE src=? OR dst=?",
                                  (cur, cur)).fetchall():
                other = r["dst"] if r["src"] == cur else r["src"]
                edges.append((r["src"], r["dst"], r["relation"], r["kind"], r["weight"]))
                if other not in nodes and len(nodes) < max_nodes:
                    nodes.add(other)
                    frontier.append((other, d + 1))
    return nodes, edges


def _adjacency(edges: list[tuple]) -> dict[int, list[tuple[int, str]]]:
    adj: dict[int, list[tuple[int, str]]] = {}
    for s, d, rel, _k, _w in edges:
        adj.setdefault(s, []).append((d, rel))
        adj.setdefault(d, []).append((s, rel))
    return adj


def candidate_paths(seed_ids: list[int], edges: list[tuple], max_len: int = 3,
                    max_paths: int = 60) -> list[list[tuple[int, str]]]:
    """BFS de caminos (nodo, relación) entre semillas y su vecindario."""
    adj = _adjacency(edges)
    paths: list[list[tuple[int, str]]] = []
    for s in seed_ids:
        queue: deque = deque([[(s, "")]])
        seen_paths = 0
        while queue and seen_paths < max_paths:
            path = queue.popleft()
            if len(path) > 1:
                paths.append(path)
                seen_paths += 1
            if len(path) > max_len:
                continue
            for nxt, rel in adj.get(path[-1][0], []):
                if any(n == nxt for n, _ in path):
                    continue
                queue.append(path + [(nxt, rel)])
    return paths[:max_paths]


def rank_paths_llm(query: str, paths: list[list[tuple[int, str]]], top_m: int = 10) -> list[tuple[float, list]]:
    """LPRA: Gemini puntúa relevancia 0-10 de cada camino; fallback = 1.0."""
    if not paths:
        return []
    labels = {}
    with storage.get_conn() as conn:
        for r in conn.execute("SELECT id, kind, label FROM nodes").fetchall():
            labels[r["id"]] = f"{r['kind']}:{r['label']}"
    rendered = []
    for i, p in enumerate(paths):
        steps = [labels.get(p[0][0], str(p[0][0]))]
        for node, rel in p[1:]:
            steps.append(f"--[{rel}]--> {labels.get(node, str(node))}")
        rendered.append(f"{i}: {' '.join(steps)}")
    prompt = ("Puntúa de 0 a 10 la relevancia de cada camino para responder la pregunta. "
              "Devuelve SOLO líneas 'i: puntuación'.\n\nPregunta: " + query +
              "\n\nCaminos:\n" + "\n".join(rendered[:40]))
    scores = _parse_scores(generate(prompt, max_tokens=1024), len(paths))
    if not scores:
        return [(1.0, p) for p in paths[:top_m]]
    ranked = sorted(zip(scores, paths), key=lambda x: -x[0])
    return ranked[:top_m]


def _parse_scores(text: str, n: int) -> list[float]:
    import re
    scores = [0.0] * n
    for m in re.finditer(r"(\d+)\s*:\s*(\d+(?:\.\d+)?)", text):
        i, v = int(m.group(1)), float(m.group(2))
        if 0 <= i < n:
            scores[i] = min(10.0, v)
    return scores if any(scores) else []


def dual_view_filter(nodes: set[int], edges: list[tuple], seed: int = 0) -> tuple[set[int], list[tuple]]:
    """Dos vistas BFS con distinto ancho; conserva el núcleo estable (intersección)."""
    rng = random.Random(seed)
    e1 = [e for e in edges if rng.random() < 0.85]
    e2 = [e for e in edges if rng.random() < 0.85]
    n1 = {s for s, d, *_ in e1} | {d for s, d, *_ in e1}
    n2 = {s for s, d, *_ in e2} | {d for s, d, *_ in e2}
    core = (n1 & n2) | (nodes & (n1 | n2))
    stable = [e for e in edges if e[0] in core and e[1] in core]
    return core, stable


def structural_scores(paths: list[list[tuple[int, str]]], seed_ids: list[int],
                        edges: list[tuple]) -> list[tuple[float, list]]:
    """Ranking sin LLM: peso estructural (aristas) + cobertura de semillas."""
    w = {(s, d, r): wt for s, d, r, _k, wt in edges}
    w.update({(d, s, r): wt for s, d, r, _k, wt in edges})
    scored = []
    for p in paths:
        nodes = [n for n, _ in p]
        cover = len(set(nodes) & set(seed_ids))
        total = sum(w.get((a, b, r), 0.5) for (a, _), (b, r) in itertools.pairwise(p))
        scored.append((cover * 2.0 + total, p))
    return sorted(scored, key=lambda x: -x[0])


def retrieve_evidence(query: str, top_m: int = 8, use_llm: bool = True) -> list[dict]:
    """Pipeline PEARL completo: semillas → subgrafo → caminos → ranking → evidencia."""
    seeds = seed_nodes(query)
    if not seeds:
        return []
    seed_ids = [s.id for s in seeds]
    nodes, edges = contextual_subgraph(seed_ids)
    nodes, edges = dual_view_filter(nodes, edges)
    paths = candidate_paths(seed_ids, edges)
    ranked = rank_paths_llm(query, paths, top_m=top_m) if use_llm else structural_scores(paths, seed_ids, edges)[:top_m]
    labels = {}
    with storage.get_conn() as conn:
        for r in conn.execute("SELECT id, kind, label, metadata FROM nodes").fetchall():
            meta = json.loads(r["metadata"]) if r["metadata"] else {}
            labels[r["id"]] = {"kind": r["kind"], "label": r["label"], "doc_id": meta.get("doc_id")}
    out = []
    for score, path in ranked:
        steps = [{"label": labels.get(n, {}).get("label", str(n)),
                  "kind": labels.get(n, {}).get("kind", "?"), "via": rel} for n, rel in path]
        docs = sorted({labels[n]["doc_id"] for n, _ in path if labels.get(n, {}).get("doc_id")})
        out.append({"score": round(score, 2), "steps": steps, "doc_ids": docs})
    return out
