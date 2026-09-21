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
)
from bibliotecario.background import run_cycle
from bibliotecario.core import storage
from bibliotecario.ingest import pipeline
from bibliotecario.knowledge import seed as SEED

__all__ = [
    "answer_multi_hop",
    "ask",
    "blueprint",
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
    return build_blueprint(technique, goal)


def implement(technique: str, goal: str) -> dict:
    return instantiate_agent_template(technique, goal)


def evolve() -> dict:
    """Ciclo de co-evolución en background (consolidar + refinar)."""
    return run_cycle()


def status() -> dict:
    return get_status()
