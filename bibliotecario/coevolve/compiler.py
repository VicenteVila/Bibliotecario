"""Compilador 0-token: estudios -> memoria y grafo -> skills.

El conocimiento ya pagado (10 estudios WikiSkill y el grafo procedimental) no
llegaba a las tablas que el producto usa: `memory_items=0` y `skills=0`. Este
módulo lo materializa de forma determinista, sin LLM ni embeddings, y deja una
foto read-only del pool Task-CoEvolve para planificar la siguiente medición.

`apply=False` es el modo por defecto: informa qué haría y no escribe. La
escritura real exige `--apply` explícito.
"""
from __future__ import annotations

import re
import statistics
import unicodedata

from bibliotecario.coevolve import selector, task_pool, wiki
from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import procedural as P
from bibliotecario.memory import memory_tree as MT

MEMORY_MARK = "[study:"
SKILL_PREFIX = "tech_skill_"
GATE_FLOOR = 0.6


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    out = re.sub(r"[^a-z0-9]+", "_", ascii_text.lower()).strip("_")
    return out[:80] or "sin_nombre"


def _memory_mark(slug: str) -> str:
    return f"{MEMORY_MARK}{slug}]"


def _memory_row(conn, slug: str):
    mark = _memory_mark(slug)
    return conn.execute(
        "SELECT id, content FROM memory_items WHERE substr(content, 1, ?)=? LIMIT 1",
        (len(mark), mark)).fetchone()


def _memory_content(page: dict) -> str:
    return f"{_memory_mark(page['slug'])} {page['title']}\n\n{page['body']}"


def compile_studies(*, apply: bool = False) -> dict:
    """Un item L2 por página `study`, idempotente por slug.

    Si el cuerpo cambió, se actualiza el mismo item en vez de dejar memoria
    obsoleta o crear un duplicado.
    """
    with storage.get_conn() as conn:
        pages = [dict(r) for r in conn.execute(
            "SELECT slug, title, body FROM wiki_pages WHERE kind='study' ORDER BY id"
        ).fetchall()]
        rows = {p["slug"]: _memory_row(conn, p["slug"]) for p in pages}
    existing = [slug for slug, row in rows.items() if row is not None]
    created: list[str] = []
    updated: list[str] = []
    for page in pages:
        content = _memory_content(page)
        row = rows[page["slug"]]
        if row is not None:
            if row["content"] == content:
                continue
            if apply:
                with storage.get_conn() as conn:
                    conn.execute(
                        "UPDATE memory_items SET content=?, strength=1.0, "
                        "last_access=datetime('now') WHERE id=?",
                        (content, row["id"]))
            updated.append(page["slug"])
            continue
        if apply:
            MT.add(content, level="L2")
        created.append(page["slug"])
    return {
        "studies": len(pages),
        "existing": len(existing),
        "created": len(created),
        "created_slugs": created,
        "updated": len(updated),
        "updated_slugs": updated,
        "apply": apply,
    }


def _ordered_procedures(labels: list[str], edges: list[tuple[str, str, str]]) -> list[str]:
    """Orden topológico estable; si hay ciclo, completa por orden alfabético."""
    valid = set(labels)
    adj: dict[str, list[str]] = {label: [] for label in labels}
    indeg = {label: 0 for label in labels}
    for src, _relation, dst in edges:
        if src in valid and dst in valid:
            adj[src].append(dst)
            indeg[dst] += 1
    ready = sorted(label for label in labels if indeg[label] == 0)
    out: list[str] = []
    while ready:
        label = ready.pop(0)
        out.append(label)
        for dst in adj[label]:
            indeg[dst] -= 1
            if indeg[dst] == 0:
                ready.append(dst)
                ready.sort()
    out.extend(sorted(valid - set(out)))
    return out


def _skill_text(technique: str, ordered: list[str],
                edges: list[tuple[str, str, str]]) -> tuple[str, str]:
    chain = " -> ".join(ordered)
    relations = "; ".join(f"{src} {rel} {dst}" for src, rel, dst in edges[:12])
    skill_md = (
        f"trigger: {technique}\n"
        f"intervention: Aplicar los procedimientos del grafo en orden: {chain}."
        + (f" Relaciones: {relations}." if relations else "")
    )
    purpose = (
        f"Skill compilada del grafo para la técnica {technique}: "
        f"{len(ordered)} procedimientos y {len(edges)} relaciones."
    )
    return skill_md, purpose


def _technique_edges(conn, proc_ids: list[int]) -> list[tuple[int, int, str]]:
    if not proc_ids:
        return []
    marks = ",".join("?" * len(proc_ids))
    rows = conn.execute(
        f"SELECT src, dst, relation FROM edges WHERE kind='procedural' "
        f"AND src IN ({marks}) AND dst IN ({marks})", [*proc_ids, *proc_ids]
    ).fetchall()
    return [(r["src"], r["dst"], r["relation"]) for r in rows]


def compile_skills(*, apply: bool = False) -> dict:
    """Un skill `tech_skill_*` por técnica con procedimientos en el grafo."""
    techniques = G.find_nodes("", kind="technique", limit=500)
    created: list[str] = []
    updated: list[str] = []
    skipped: list[str] = []
    for tech in techniques:
        procs = P.list_procedures(tech.label)
        if not procs:
            skipped.append(tech.label)
            continue
        by_id = {p.id: p.label for p in procs}
        with storage.get_conn() as conn:
            raw_edges = _technique_edges(conn, list(by_id))
        edges = [(by_id[src], rel, by_id[dst]) for src, dst, rel in raw_edges]
        ordered = _ordered_procedures([p.label for p in procs], edges)
        skill_md, purpose = _skill_text(tech.label, ordered, edges)
        name = SKILL_PREFIX + _slug(tech.label)
        with storage.get_conn() as conn:
            row = conn.execute(
                "SELECT skill_md, purpose_md FROM skills WHERE name=?", (name,)
            ).fetchone()
        if row is not None and row["skill_md"] == skill_md and (row["purpose_md"] or "") == purpose:
            continue
        coverage = len(edges) / max(1, len(ordered) - 1)
        score = min(1.0, GATE_FLOOR + 0.4 * coverage)
        if apply:
            wiki.gate_skill(name, skill_md, purpose, score)
        if row is None:
            created.append(name)
        else:
            updated.append(name)
    with storage.get_conn() as conn:
        total = conn.execute(
            "SELECT COUNT(*) c FROM skills WHERE name GLOB 'tech_skill_*'"
        ).fetchone()["c"]
    return {
        "techniques": len(techniques),
        "created": len(created),
        "updated": len(updated),
        "skipped": skipped,
        "created_names": created,
        "updated_names": updated,
        "total_tech_skills": total,
        "apply": apply,
    }


def snapshot(rho: float = 0.2, seed: int = 0) -> dict:
    """Foto read-only del pool: qué tareas se muestrearían y con qué pesos."""
    if not 0 < rho <= 1:
        raise ValueError("rho debe estar en (0, 1]")
    stats = task_pool.task_stats()
    if not stats:
        return {"tasks": 0, "outcomes": 0, "rho": rho, "seed": seed,
                "sample": [], "estimator": "no aplica: pool vacío"}
    weights = selector.weights(stats)
    pbar = [s["pbar"] for s in stats]
    return {
        "tasks": len(stats),
        "outcomes": sum(s["n"] for s in stats),
        "pbar_mean": round(statistics.mean(pbar), 4),
        "pbar_ones": sum(1 for p in pbar if p == 1.0),
        "pbar_zeros": sum(1 for p in pbar if p == 0.0),
        "weight_min": round(min(weights.values()), 4),
        "weight_max": round(max(weights.values()), 4),
        "rho": rho,
        "seed": seed,
        "sample": selector.sample_subset(stats, rho, seed=seed),
        "estimator": "no aplica: sin outcomes de un candidato nuevo",
    }


def run(*, apply: bool = False) -> dict:
    return {
        "apply": apply,
        "llm_tokens": 0,
        "studies": compile_studies(apply=apply),
        "skills": compile_skills(apply=apply),
        "coevolve": snapshot(),
    }
