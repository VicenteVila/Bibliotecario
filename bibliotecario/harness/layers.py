"""Las 4 capas LIFE-HARNESS porteadas: contrato, skills, realización, regulación."""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class EnvironmentContractLayer:
    """Calibra definiciones de tools antes de enviarlas al LLM."""

    def __init__(self) -> None:
        self._cache: dict[str, dict] = {}
        self.corrections = 0

    def calibrate_tools(self, tools: list[dict]) -> list[dict]:
        out = []
        for tool in tools:
            if tool.get("type") != "function":
                out.append(tool)
                continue
            name = tool.get("function", {}).get("name", "")
            if name in self._cache:
                out.append(self._cache[name])
                continue
            calibrated = self._calibrate(tool)
            self._cache[name] = calibrated
            out.append(calibrated)
        return out

    def _calibrate(self, tool: dict) -> dict:
        func, params = tool.get("function", {}), tool.get("function", {}).get("parameters", {})
        required = params.setdefault("required", [])
        for pname, prop in params.get("properties", {}).items():
            if prop.get("required", False) and pname not in required:
                required.append(pname)
                self.corrections += 1
            if "type" not in prop:
                prop["type"] = "string"
                self.corrections += 1
            if "enum" in prop and not prop["enum"]:
                del prop["enum"]
                self.corrections += 1
        if len(func.get("description", "")) > 500:
            func["description"] = func["description"][:497] + "..."
            self.corrections += 1
        return tool


@dataclass
class ProceduralSkill:
    name: str
    trigger_patterns: list[str]
    intervention: str
    success_rate: float = 0.5
    invocation_count: int = 0
    success_count: int = 0

    def record_outcome(self, success: bool) -> None:
        self.invocation_count += 1
        if success:
            self.success_count += 1
        self.success_rate = self.success_count / max(1, self.invocation_count)


class ProceduralSkillLayer:
    def __init__(self) -> None:
        self._skills: dict[str, ProceduralSkill] = {}
        self._failures: list[dict] = []

    def register_skill(self, skill: ProceduralSkill) -> None:
        self._skills[skill.name] = skill

    def retrieve_skills(self, task: str, state: dict) -> list[ProceduralSkill]:
        err = state.get("last_error", "")
        matched = [s for s in self._skills.values()
                   if any(re.search(p, task, re.IGNORECASE) or (err and re.search(p, err, re.IGNORECASE))
                          for p in s.trigger_patterns)]
        return sorted(matched, key=lambda s: s.success_rate, reverse=True)[:3]

    def record_failure(self, task: str, error: str, trajectory: list) -> None:
        self._failures.append({"task": task, "error": error, "trajectory": trajectory[-10:]})
        self._failures = self._failures[-500:]


@dataclass
class ActionValidation:
    valid: bool
    canonicalized: Any = None
    error: str | None = None


class ActionRealizationLayer:
    """Valida y canoniza llamadas a tools pre-ejecución."""

    def __init__(self) -> None:
        self.passed = 0
        self.failed = 0
        self.corrected = 0

    def validate_tool_call(self, name: str, args: Any, tools: list[dict]) -> ActionValidation:
        if not name:
            self.failed += 1
            return ActionValidation(False, error="Llamada vacía")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                self.failed += 1
                return ActionValidation(False, error="Argumentos no son JSON válido")
        if not isinstance(args, dict):
            self.failed += 1
            return ActionValidation(False, error="Argumentos deben ser objeto")
        spec = next((t for t in tools if t.get("function", {}).get("name") == name), None)
        if spec is None:
            self.failed += 1
            return ActionValidation(False, error=f"Tool desconocida: {name}")
        params = spec.get("function", {}).get("parameters", {})
        for req in params.get("required", []):
            if req not in args:
                props = params.get("properties", {})
                if req in props and "default" in props[req]:
                    args[req] = props[req]["default"]
                    self.corrected += 1
                else:
                    self.failed += 1
                    return ActionValidation(False, error=f"Falta requerido: {req}")
        for key, value in list(args.items()):
            if params.get("properties", {}).get(key, {}).get("type") == "integer" and isinstance(value, float):
                args[key] = int(value)
                self.corrected += 1
        self.passed += 1
        return ActionValidation(True, canonicalized={"name": name, "arguments": args})


@dataclass
class TrajectoryState:
    actions: list = field(default_factory=list)
    stagnation_count: int = 0
    invalid_retry_count: int = 0
    last_hash: int | None = None
    start_time: float = field(default_factory=time.time)
    budget_exhausted: bool = False

    def record_action(self, action: dict) -> None:
        self.actions.append(action)
        h = hash(json.dumps(action, sort_keys=True, default=str))
        self.stagnation_count = self.stagnation_count + 1 if h == self.last_hash else 0
        self.last_hash = h


class TrajectoryRegulationLayer:
    def __init__(self, max_stagnation: int = 3, max_retries: int = 5,
                 max_actions: int = 40, max_duration: float = 600.0):
        self.max_stagnation, self.max_retries = max_stagnation, max_retries
        self.max_actions, self.max_duration = max_actions, max_duration
        self._sessions: dict[str, TrajectoryState] = {}
        self.recoveries = 0

    def state(self, sid: str) -> TrajectoryState:
        return self._sessions.setdefault(sid, TrajectoryState())

    def check_all(self, sid: str) -> list[str]:
        st, out = self.state(sid), []
        if st.stagnation_count >= self.max_stagnation:
            st.stagnation_count = 0
            self.recoveries += 1
            out.append("[REGULACIÓN] Bucle de acciones repetidas: cambia de estrategia.")
        if st.invalid_retry_count >= self.max_retries:
            st.invalid_retry_count = 0
            self.recoveries += 1
            out.append("[REGULACIÓN] Reintentos inválidos consecutivos: valida antes de actuar.")
        if len(st.actions) >= self.max_actions or time.time() - st.start_time >= self.max_duration:
            st.budget_exhausted = True
            self.recoveries += 1
            out.append("[REGULACIÓN] Presupuesto agotado: responde con lo disponible.")
        return out

    def cleanup(self, sid: str) -> None:
        self._sessions.pop(sid, None)
