"""Refiner del grafo procedimental: contrasta trayectorias fallidas vs exitosas y muta el grafo.

Mutaciones: add_procedure | add_link | update_weight | merge | note.
Persistencia dual: SQLite (grafo) + lessons (tabla) + markdown legible en data/lessons/.
"""
from __future__ import annotations

import json
import logging

from bibliotecario.config import data_dir
from bibliotecario.core import storage
from bibliotecario.core.llm import generate
from bibliotecario.knowledge import procedural as P

logger = logging.getLogger(__name__)


def propose_mutations(failed: list[str], succeeded: list[str], scope: str) -> list[dict]:
    prompt = (
        "Contrasta estas trayectorias de un agente de búsqueda.\n\nFALLIDAS:\n- " +
        "\n- ".join(failed[:8]) + "\n\nEXITOSAS:\n- " + "\n- ".join(succeeded[:8]) +
        "\n\nPropón mutaciones al grafo procedimental como JSON array con objetos "
        '{"op": "add_procedure|add_link|update_weight|note", "label"?, "relation"?, "target"?, '
        '"weight"?, "text"?}. Solo el JSON.'
    )
    out = generate(prompt, max_tokens=1024)
    if not out:
        return []
    try:
        start, end = out.index("["), out.rindex("]") + 1
        muts = json.loads(out[start:end])
        return [m for m in muts if isinstance(m, dict) and m.get("op")]
    except (ValueError, json.JSONDecodeError) as e:
        logger.warning("Refiner: JSON inválido: %s", e)
        return []


def apply_mutations(mutations: list[dict], scope: str) -> dict:
    applied = {"add_procedure": 0, "add_link": 0, "update_weight": 0, "note": 0}
    notes: list[str] = []
    for m in mutations:
        op = m.get("op")
        try:
            if op == "add_procedure" and m.get("label"):
                P.register_procedure(m["label"], description=m.get("text", ""))
                applied["add_procedure"] += 1
            elif op == "add_link" and m.get("label") and m.get("target") and m.get("relation"):
                rel = m["relation"] if m["relation"] in P.RELATIONS else "refines"
                P.link(m["label"], rel, m["target"], weight=float(m.get("weight", 1.0)))
                applied["add_link"] += 1
            elif op == "update_weight" and m.get("label") and m.get("target"):
                P.link(m["label"], m.get("relation", "refines") if m.get("relation") in P.RELATIONS else "refines",
                       m["target"], weight=float(m.get("weight", 1.0)))
                applied["update_weight"] += 1
            elif op == "note" and m.get("text"):
                notes.append(m["text"])
                applied["note"] += 1
        except (ValueError, TypeError, KeyError) as e:
            logger.warning("Refiner: mutación inválida %s: %s", m, e)
    if notes:
        save_lesson(scope, what_worked="", what_failed="", key_insights="\n".join(notes))
    return applied


def save_lesson(scope: str, what_worked: str, what_failed: str, key_insights: str) -> int:
    with storage.get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO lessons (scope, what_worked, what_failed, key_insights) VALUES (?,?,?,?)",
            (scope, what_worked, what_failed, key_insights))
        lid = cur.lastrowid
    md = (f"# Lesson {lid} — {scope}\n\n## What Worked\n{what_worked}\n\n"
          f"## What Didn't Work\n{what_failed}\n\n## Key Insights\n{key_insights}\n")
    path = data_dir() / "lessons"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{lid:04d}-{scope}.md").write_text(md, encoding="utf-8")
    return lid


def refine_from_trajectories(failed: list[str], succeeded: list[str], scope: str) -> dict:
    if not failed and not succeeded:
        return {"applied": {}, "note": "sin trayectorias"}
    muts = propose_mutations(failed, succeeded, scope)
    if not muts:
        return {"applied": {}, "note": "sin propuestas (¿falta LLM?)"}
    return {"applied": apply_mutations(muts, scope)}
