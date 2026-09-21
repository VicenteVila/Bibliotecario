"""RuntimeHarness: combina las 4 capas + registro PF + persistencia de runs.

Fixes vs origen: harness habilitado por defecto; runs persistidos en harness_runs
(corrige 'cero persistencia'); estado PF consultable para validación Task-CoEvolve.
"""
from __future__ import annotations

import json
import logging
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
        with storage.get_conn() as conn:
            conn.execute("UPDATE harness_runs SET finished_at=datetime('now'), score=?, metadata=? WHERE id=?",
                         (score, json.dumps(metadata or {}, ensure_ascii=False), run_id))

    def stats(self) -> dict[str, Any]:
        return {"interventions": self._interventions, "pfs": self.pfs.stats(),
                "action_pass_rate": self.actions.passed / max(1, self.actions.passed + self.actions.failed)}


_harness: RuntimeHarness | None = None


def get_harness() -> RuntimeHarness:
    global _harness
    if _harness is None:
        _harness = RuntimeHarness()
    return _harness
