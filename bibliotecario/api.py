"""API pública de librería Bibliotecario."""
from __future__ import annotations

from bibliotecario.agent import loop as LOOP
from bibliotecario.agent.tools import (
    answer_multi_hop,
    build_blueprint,
    get_paper,
    get_status,
    instantiate_agent_template,
    register_skill,
    retrieve_evidence,
    search_papers,
    verify_and_mark,
    verify_and_repair,
)
from bibliotecario.background import run_cycle
from bibliotecario.core import storage
from bibliotecario.ingest import pipeline
from bibliotecario.knowledge import seed as SEED

__all__ = [
    "answer_multi_hop",
    "ask",
    "blueprint",
    "blueprint_loop",
    "blueprint_verified",
    "build_blueprint",
    "evolve",
    "get_paper",
    "implement",
    "ingest",
    "ingest_dir",
    "init",
    "instantiate_agent_template",
    "register_skill",
    "retrieve_evidence",
    "search_papers",
    "status",
    "verify_and_mark",
    "verify_and_repair",
]


def init() -> dict:
    storage.init_db()
    return SEED.seed()


def ingest(source: str, ocr: bool = False):
    return pipeline.ingest(source, ocr=ocr)


def ingest_dir(directory: str, ocr: bool = False) -> dict:
    return pipeline.ingest_dir(directory, ocr=ocr)


def ask(question: str, max_turns: int = 10) -> dict:
    return LOOP.run(question, max_turns=max_turns)


def blueprint(technique: str, goal: str) -> dict:
    """Brazo B del A/B (§5.7): un solo `generate()` con P2. Sin loop."""
    return build_blueprint(technique, goal)


def blueprint_loop(technique: str, goal: str, max_turns: int = 4) -> dict:
    """Brazo C del A/B (§5.7): P1' — el loop reúne evidencia, la tool escribe."""
    return LOOP.run_blueprint(technique, goal, max_turns=max_turns)


def blueprint_verified(technique: str, goal: str) -> dict:
    """Brazo D (§5): P1' + P2 + P3 — el loop reúne, la tool escribe, se verifica.

    Es C **más** P3, no P3 solo. La primera versión del brazo llamaba a
    `build_blueprint_verified`, que se salta el loop: perdió lo único que P1'
    aportaba (citas que resuelven) y salió con B8=0,00 — peor que el brazo C
    que pretendía mejorar.
    """
    return verify_and_repair(LOOP.run_blueprint(technique, goal))


def implement(technique: str, goal: str) -> dict:
    return instantiate_agent_template(technique, goal)


def evolve() -> dict:
    """Ciclo de co-evolución en background (consolidar + refinar)."""
    return run_cycle()


def status() -> dict:
    return get_status()
