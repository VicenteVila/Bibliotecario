"""RuntimeHarness: combina las 4 capas + registro PF + persistencia de runs.

Fixes vs origen: harness habilitado por defecto; runs persistidos en harness_runs
(corrige 'cero persistencia'); estado PF consultable para validación Task-CoEvolve.

harness_runs.score se rellena desde fuera con record_score(): el loop no tiene
juez. Un score NULL significa "nadie lo midió", no "fue 0", y por eso las runs
de infraestructura se quedan sin puntuar en lugar de bajar la media.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import uuid
from typing import Any

from bibliotecario.core import storage
from bibliotecario.harness import edits as ED
from bibliotecario.harness.layers import (
    ActionRealizationLayer,
    EnvironmentContractLayer,
    ProceduralSkill,
    ProceduralSkillLayer,
    TrajectoryRegulationLayer,
)
from bibliotecario.harness.pfs import SkillProgramRegistry, get_pf_registry
from bibliotecario.memory import memory_tree as MT

logger = logging.getLogger(__name__)

# Intervención derivada de la firma (Hito 4): solo retry y fallback.
# decompose no se usa porque exigiría task.complexity, que el loop no conoce
# y no se inventa — la misma regla de la Fase 1 que deja DecomposePF quieto.
_SKILL_TEXT = {
    "retry": "este fallo ya se repitió: reintenta con parámetros modificados, no repitas la misma llamada",
    "fallback": "este fallo ya se repitió: si el LLM sigue fallando, degrada a respuesta extractiva con la evidencia disponible",
}


def _pick_intervention(signature: str) -> str:
    s = signature.lower()
    if any(w in s for w in ("fallo llm", "vacio", "vacío", "timeout", "turno vac")):
        return "fallback"
    return "retry"


def _persist_skill(name: str, signature: str, intervention: str) -> None:
    """Misma upsert que tools.register_skill, sin importar agent.tools (ciclo de imports)."""
    skill_md = f"trigger: {signature}\nintervention: {intervention}"
    with storage.get_conn() as conn:
        conn.execute(
            "INSERT INTO skills (name, skill_md, purpose_md) VALUES (?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET skill_md=excluded.skill_md, "
            "purpose_md=excluded.purpose_md, updated_at=datetime('now')",
            (name, skill_md,
             "skill evolucionada desde fallos recurrentes (Hito 4, hallazgo 4)"))


def _read_metadata(conn, run_id: str) -> dict:
    """Metadata ya escrita de una run. Nunca lanza: un JSON roto no debe tumbar un UPDATE."""
    row = conn.execute("SELECT metadata FROM harness_runs WHERE id=?", (run_id,)).fetchone()
    if row is None:
        return {}
    try:
        data = json.loads(row["metadata"] or "{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


class RuntimeHarness:
    def __init__(self, pf_registry: SkillProgramRegistry | None = None) -> None:
        self.contract = EnvironmentContractLayer()
        self.skills = ProceduralSkillLayer()
        try:
            self.skills.load_from_db()
        except sqlite3.OperationalError as e:
            if "no such table" not in str(e).lower():
                raise
            logger.warning("skills no rehidratadas (DB sin init): %s", e)
        self.actions = ActionRealizationLayer()
        self.trajectory = TrajectoryRegulationLayer()
        self.pfs = pf_registry or get_pf_registry()
        self._interventions = 0

    def calibrate(self, tools: list[dict]) -> list[dict]:
        return self.contract.calibrate_tools(tools)

    def apply_pfs(self, state: dict) -> list[dict]:
        """Ejecuta PFs coincidentes (origen nunca lo cableaba al loop)."""
        results = self.pfs.execute_matching(state)
        self._interventions += len(results)
        return results

    def validate_call(self, name: str, args: Any, tools: list[dict]):
        return self.actions.validate_tool_call(name, args, tools)

    def record_action(self, sid: str, action: dict) -> None:
        self.trajectory.state(sid).record_action(action)

    def record_error(self, sid: str) -> None:
        self.trajectory.state(sid).invalid_retry_count += 1

    def regulate(self, sid: str) -> list[str]:
        out = self.trajectory.check_all(sid)
        self._interventions += len(out)
        return out

    # -- meta-evolución (Hito 4, hallazgo 4) --------------------------------
    def skill_hints(self, task: str, last_error: str) -> list[tuple[ProceduralSkill, str]]:
        """Skills que aplican a este error, con su hint ya formateado para la historia."""
        return [(s, f"[skill {s.name}] {s.intervention}")
                for s in self.skills.retrieve_skills(task, {"last_error": last_error})]

    def meta_evolve(self, task: str, errors: list[str]) -> list[dict]:
        """Fin de run: cuenta las firmas de fallo y evoluciona a la 2ª (K=2).

        Devuelve los eventos de evolución de esta run (vacío si no tocaba).
        `errors` llega deduplicado y normalizado desde el loop, y una firma ya
        evolucionada no se vuelve a tocar. Lo que registra por evolución:
        PF auto en el registro, skill en la capa y en la tabla skills, y el
        evento en memory_items (L0) para que background.consolidate lo vea.
        """
        events: list[dict] = []
        for sig in errors:
            try:
                row = ED.bump(sig)
            except sqlite3.OperationalError as e:
                if "no such table" not in str(e).lower():
                    raise
                logger.warning(
                    "harness_edits ausente: la meta-evolución no persiste "
                    "(ejecuta storage.init_db()): %s", e)
                return events
            if row["occurrences"] < ED.MIN_RUNS or row["evolved"]:
                continue
            intervention = _pick_intervention(sig)
            if not ED.claim_evolution(sig):
                continue  # otro hilo la evolucionó primero
            pattern = {"trigger": sig, "field": "last_error", "intervention": intervention}
            try:
                names = self.pfs.evolve_from_failures([pattern])
            except Exception:
                ED.release_claim(sig)
                raise
            pf_name = names[0]
            ED.mark_evolved(sig, pf_name, pattern)
            skill = ProceduralSkill(
                name=f"auto_skill_{pf_name.rsplit('_', 1)[-1]}",
                trigger_patterns=[re.escape(sig)],
                intervention=_SKILL_TEXT[intervention])
            self.skills.register_skill(skill)
            _persist_skill(skill.name, sig, skill.intervention)
            MT.add(f"meta-evolución: '{sig}' -> {pf_name}", level="L0")
            events.append({"signature": sig, "pf": pf_name, "skill": skill.name,
                           "occurrences": row["occurrences"], "intervention": intervention})
            logger.info("meta-evolución: firma x%d -> %s (+skill %s)",
                        row["occurrences"], pf_name, skill.name)
        return events

    # -- persistencia de runs -------------------------------------------------
    def start_run(self, metadata: dict | None = None) -> str:
        rid = uuid.uuid4().hex[:12]
        with storage.get_conn() as conn:
            conn.execute("INSERT INTO harness_runs (id, metadata) VALUES (?,?)",
                         (rid, json.dumps(metadata or {}, ensure_ascii=False)))
        return rid

    def finish_run(self, run_id: str, score: float | None, metadata: dict | None = None) -> None:
        """Cierra la run. Fusiona la metadata en vez de sobrescribirla.

        Antes el UPDATE pisaba la que start_run escribió, así que la `question`
        desaparecía y una fila de harness_runs era anónima: un score sin saber
        qué pregunta lo produjo no sirve para auditar nada.
        """
        with storage.get_conn() as conn:
            merged = _read_metadata(conn, run_id)
            merged.update(metadata or {})
            conn.execute("UPDATE harness_runs SET finished_at=datetime('now'), score=?, metadata=? WHERE id=?",
                         (score, json.dumps(merged, ensure_ascii=False), run_id))

    def record_score(self, run_id: str, score: float | None,
                     metadata: dict | None = None) -> bool:
        """Escribe el score que una evaluación calculó fuera del loop.

        El loop no tiene juez, así que el score siempre viene de fuera y solo
        cuando alguien evalúa. Devuelve False si la run no existe: el caller
        decide si eso es un problema, no el harness.

        Solo toca la fila de `run_id`, así que con `--workers 5` (cada hilo con
        su run) no hay carrera: una run nunca escribe la de otra.
        """
        with storage.get_conn() as conn:
            if conn.execute("SELECT 1 FROM harness_runs WHERE id=?", (run_id,)).fetchone() is None:
                return False
            merged = _read_metadata(conn, run_id)
            merged.update(metadata or {})
            conn.execute("UPDATE harness_runs SET score=?, metadata=? WHERE id=?",
                         (score, json.dumps(merged, ensure_ascii=False), run_id))
        return True

    def stats(self) -> dict[str, Any]:
        return {"interventions": self._interventions, "pfs": self.pfs.stats(),
                "action_pass_rate": self.actions.passed / max(1, self.actions.passed + self.actions.failed)}


_local = threading.local()


def get_harness() -> RuntimeHarness:
    """Harness por hilo.

    Antes era un singleton de módulo: con `--workers 4` las cuatro preguntas
    paralelas compartían un harness, así que el calibrate() de una pisaba el
    de otra y los contadores (interventions, actions.passed/failed) se
    mezclaban entre preguntas distintas. El estado de una pregunta no puede
    depender del orden de intercalado de los hilos, o la evaluación deja de
    ser repetible. En producción el hilo es único, así que el comportamiento
    no cambia.
    """
    harness = getattr(_local, "harness", None)
    if harness is None:
        harness = _local.harness = RuntimeHarness()
    return harness


def reset_harness() -> None:
    """Olvida el harness del hilo actual. Solo para tests."""
    _local.harness = None
