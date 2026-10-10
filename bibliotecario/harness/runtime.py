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
import threading
import uuid
from typing import Any

from bibliotecario.core import storage
from bibliotecario.harness.layers import (
    ActionRealizationLayer,
    EnvironmentContractLayer,
    ProceduralSkillLayer,
    TrajectoryRegulationLayer,
)
from bibliotecario.harness.pfs import SkillProgramRegistry, get_pf_registry

logger = logging.getLogger(__name__)


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
