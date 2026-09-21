"""Wiki persistente multicapa estilo WikiSkill: raw / accumulated / skill.

- raw: experiencia cruda (ingesta, trayectorias).
- accumulated: conocimiento destilado (patrones, lecciones estructuradas).
- skill: skills ejecutables (SKILL.md + PURPOSE.md).
Gating: una skill candidata solo promociona a 'skill' si supera validación (score>=umbral);
si no, rollback (se queda en accumulated con nota).
"""
from __future__ import annotations

import logging

from bibliotecario.core import storage

logger = logging.getLogger(__name__)
VALIDATE_THRESHOLD = 0.6


def upsert_page(slug: str, title: str, body: str, kind: str) -> None:
    assert kind in ("raw", "accumulated", "skill"), kind
    with storage.get_conn() as conn:
        conn.execute("INSERT INTO wiki_pages (slug, title, body, kind) VALUES (?,?,?,?) "
                     "ON CONFLICT(slug) DO UPDATE SET title=excluded.title, body=excluded.body, "
                     "kind=excluded.kind, updated_at=datetime('now')",
                     (slug, title, body, kind))


def get_page(slug: str) -> dict | None:
    with storage.get_conn() as conn:
        r = conn.execute("SELECT * FROM wiki_pages WHERE slug=?", (slug,)).fetchone()
    return dict(r) if r else None


def list_pages(kind: str | None = None) -> list[dict]:
    sql = "SELECT slug, title, kind, updated_at FROM wiki_pages"
    args: list = []
    if kind:
        sql += " WHERE kind=?"
        args.append(kind)
    with storage.get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def stratified_traces(failed: list[str], succeeded: list[str]) -> dict:
    """Muestreo estratificado para feedback del maintainer: ≤5 fallos + ≤3 éxitos."""
    return {"failed": failed[:5], "succeeded": succeeded[:3]}


def gate_skill(name: str, skill_md: str, purpose_md: str, validation_score: float) -> dict:
    """Gating+rollback: promociona a skill o la devuelve a accumulated con nota."""
    if validation_score >= VALIDATE_THRESHOLD:
        upsert_page(f"skill-{name}", name, skill_md, "skill")
        from bibliotecario.agent.tools import register_skill
        register_skill(name, skill_md, purpose_md)
        return {"promoted": True, "score": validation_score}
    upsert_page(f"skill-{name}", name,
                f"{skill_md}\n\n> RECHAZADA en gating (score={validation_score:.2f}<{VALIDATE_THRESHOLD}).\n> {purpose_md}",
                "accumulated")
    return {"promoted": False, "score": validation_score}
