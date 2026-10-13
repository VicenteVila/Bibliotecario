"""API pública de librería Bibliotecario."""
from __future__ import annotations

from bibliotecario.agent import loop as LOOP
from bibliotecario.agent.attribution import critic_and_demote
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
from bibliotecario.knowledge.study import (
    get_study,
    study_paper,
)
from bibliotecario.knowledge.study import (
    list_studies as list_studies_,
)

__all__ = [
    "answer_multi_hop",
    "ask",
    "blueprint",
    "blueprint_loop",
    "blueprint_p4",
    "blueprint_route5",
    "blueprint_verified",
    "build_blueprint",
    "evolve",
    "get_paper",
    "get_study",
    "implement",
    "ingest",
    "ingest_dir",
    "init",
    "instantiate_agent_template",
    "register_skill",
    "retrieve_evidence",
    "search_papers",
    "status",
    "study",
    "study_of",
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


def blueprint_p4(technique: str, goal: str) -> dict:
    """Brazo E (§5): P1' + P2 + P4 — mismo camino que C, con las reglas nuevas.

    Aislamiento: respecto al brazo C solo cambian `_WRITING_RULES` (R4
    redefinida por dec. 10, R6 en línea, R1 como suelo) y el verificador, que
    ahora mira números y ficheros. **No hay reescritura** — `verify_and_mark`
    devuelve el informe sin tocar el texto, que es lo que midió P3 que
    empeoraba el blueprint (§5.8.3). Así E vs C mide P4, y solo P4.
    """
    return verify_and_mark(LOOP.run_blueprint(technique, goal))


def study(doc_id: int, force: bool = False) -> dict:
    """Capa de comprensión: qué dice y qué no dice el paper.

    No es un blueprint — no se construye nada. Es el artefacto que se puede
    aprender, y el único que cruza papers entre sí (sección «Relación con otras
    técnicas»), que es lo que le da valor de transferencia entre runs.
    """
    return study_paper(doc_id, force=force)


def study_of(technique: str) -> dict:
    """Estudio del paper que documenta esa técnica."""
    from bibliotecario.knowledge import graph as G
    doc_id = None
    for n in G.find_nodes(technique, kind="technique", limit=5):
        if n.metadata.get("doc_id"):
            doc_id = n.metadata["doc_id"]
            break
    if doc_id is None:
        return {"ok": False, "error": f"sin doc_id para la técnica '{technique}'"}
    return study_paper(doc_id)


def list_studies() -> list[dict]:
    return list_studies_()


def blueprint_route5(technique: str, goal: str, *, limit: int | None = None) -> dict:
    """Ruta 5 (§5.10): C + crítico por afirmación + degradación del puntero.

    A diferencia de D (`verify_and_repair`), **no reescribe la prosa**: quita el
    puntero de lo que la fuente no sostiene y lo marca como propuesta. Es la
    acción que P3 no pudo hacer sin destruir el documento (§5.8.3).

    `limit` acota las afirmaciones criticadas — para probar barato antes de una
    evaluación completa (~10k tokens por blueprint, §5.10.1).
    """
    bp = LOOP.run_blueprint(technique, goal)
    if isinstance(bp, dict) and bp.get("doc_id") is not None:
        from bibliotecario.agent.tools import _cited_chunks
        chunks = _cited_chunks(bp["doc_id"], bp.get("blueprint", ""))
        res = critic_and_demote(bp["blueprint"], chunks, limit=limit)
        out = dict(bp)
        out["blueprint"] = res["blueprint"]
        out["route5"] = {k: res[k] for k in ("violaciones", "marcas", "reescrito",
                                            "degradadas")}
        return out
    out = dict(bp) if isinstance(bp, dict) else {"blueprint": bp}
    out["route5"] = {"violaciones": [], "marcas": {}, "reescrito": False,
                     "degradadas": 0, "nota": "sin doc_id: nada que criticar"}
    return out


def implement(technique: str, goal: str) -> dict:
    return instantiate_agent_template(technique, goal)


def evolve() -> dict:
    """Ciclo de co-evolución en background (consolidar + refinar)."""
    return run_cycle()


def status() -> dict:
    return get_status()
