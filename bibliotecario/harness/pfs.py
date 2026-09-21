"""PFs (HASP): skills ejecutables con precondiciones sobre el estado.

Fixes vs origen:
- matches() tolera claves planas Y anidadas (bug flat-vs-nested del origen).
- FallbackPF apunta a Gemini, no a ollama.
- evolve_from_failures genera nombres únicos con contador (no solo time.time()).
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

StateDict = dict[str, Any]


class ProgramFunction(ABC):
    def __init__(self, name: str, description: str, preconditions: list[tuple[str, str]], priority: int = 0):
        self.name = name
        self.description = description
        self.preconditions = preconditions
        self.priority = priority
        self.invocation_count = 0
        self.success_count = 0

    @abstractmethod
    def execute(self, state: StateDict, context: Any) -> dict[str, Any]: ...

    def matches(self, state: StateDict) -> bool:
        for field, pattern in self.preconditions:
            value = self._lookup(state, field)
            if value is None:
                return False
            if not re.search(pattern, str(value), re.IGNORECASE):
                return False
        return True

    @staticmethod
    def _lookup(state: StateDict, field: str) -> Any:
        # 1) clave plana literal ("last_action.status" como clave) 2) ruta anidada
        if field in state:
            return state[field]
        current: Any = state
        for part in field.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def record_outcome(self, success: bool) -> None:
        self.invocation_count += 1
        if success:
            self.success_count += 1


class RetryPF(ProgramFunction):
    def __init__(self) -> None:
        super().__init__("retry_on_failure", "Reintenta con parámetros modificados tras un error",
                         [("last_action.status", "error|failure|failed"), ("attempt_count", r"\d+")], priority=10)

    def execute(self, state: StateDict, context: Any) -> dict[str, Any]:
        attempt = int(state.get("attempt_count", 0))
        max_attempt = int(state.get("max_attempts", 3))
        if attempt >= max_attempt:
            return {"action": "escalate", "message": f"Intento {attempt}/{max_attempt}: escalando"}
        return {"action": "retry", "message": f"Intento {attempt}/{max_attempt}: reintentando",
                "modifications": {"temperature": 0.1 + attempt * 0.1}}


class DecomposePF(ProgramFunction):
    def __init__(self) -> None:
        super().__init__("decompose_complex_task", "Descompone tareas complejas en subtareas",
                         [("task.complexity", "high|complex|difficult"),
                          ("task.type", "research|analysis|report|implement|investigación")], priority=20)

    def execute(self, state: StateDict, context: Any) -> dict[str, Any]:
        return {"action": "decompose", "message": "Descomponiendo en subtareas",
                "subtasks": ["1) Buscar evidencia", "2) Analizar fuentes clave",
                             "3) Sintetizar hallazgos", "4) Responder con citas"]}


class FallbackPF(ProgramFunction):
    def __init__(self) -> None:
        super().__init__("fallback_on_exhaustion", "Degrada a respuesta extractiva sin LLM si Gemini falla",
                         [("last_action.status", "timeout|exhausted|error|rate_limit")], priority=30)

    def execute(self, state: StateDict, context: Any) -> dict[str, Any]:
        return {"action": "fallback", "message": "Gemini no disponible: respuesta extractiva",
                "modifications": {"mode": "extractive", "model": "gemini-fallback"}}


class ValidateBeforeActPF(ProgramFunction):
    def __init__(self) -> None:
        super().__init__("validate_before_act", "Valida la acción tras errores repetidos",
                         [("last_action.status", "error|failure"), ("error_count", r"[3-9]|\d{2,}")], priority=5)

    def execute(self, state: StateDict, context: Any) -> dict[str, Any]:
        return {"action": "validate", "message": "Validando próxima acción antes de ejecutar",
                "validate_fields": ["tool_name", "arguments", "format"]}


class SkillProgramRegistry:
    def __init__(self) -> None:
        self._pfs: dict[str, ProgramFunction] = {}
        self._auto_evolved = 0

    def register(self, pf: ProgramFunction) -> None:
        self._pfs[pf.name] = pf

    def register_builtins(self) -> None:
        for cls in (RetryPF, DecomposePF, FallbackPF, ValidateBeforeActPF):
            pf = cls()
            self._pfs.setdefault(pf.name, pf)

    def find_matching(self, state: StateDict) -> list[ProgramFunction]:
        matched = []
        for pf in self._pfs.values():
            try:
                if pf.matches(state):
                    matched.append(pf)
            except re.error as e:
                logger.warning("PF %s patrón inválido: %s", pf.name, e)
        return sorted(matched, key=lambda p: p.priority, reverse=True)

    def execute_matching(self, state: StateDict, context: Any = None) -> list[dict[str, Any]]:
        out = []
        for pf in self.find_matching(state):
            try:
                res = pf.execute(state, context)
                out.append({"pf": pf.name, **res})
                pf.record_outcome(res.get("action") != "error")
            except Exception as e:
                logger.error("PF %s falló: %s", pf.name, e)
                pf.record_outcome(False)
                out.append({"pf": pf.name, "action": "error", "message": str(e)})
        return out

    def evolve_from_failures(self, failure_patterns: list[dict[str, Any]]) -> int:
        n = 0
        for pattern in failure_patterns:
            self._auto_evolved += 1
            name = f"auto_pf_{self._auto_evolved}"
            kind = pattern.get("intervention", "retry")
            pf = {"decompose": DecomposePF, "fallback": FallbackPF}.get(kind, RetryPF)()
            pf.name = name
            trigger = re.escape(str(pattern.get("trigger", ""))[:50])
            pf.preconditions = [(pattern.get("field", "last_action.status"), trigger or "error")]
            self.register(pf)
            n += 1
        return n

    def stats(self) -> dict[str, Any]:
        return {"total": len(self._pfs), "auto_evolved": self._auto_evolved,
                "pfs": [{"name": p.name, "invocations": p.invocation_count,
                         "success": p.success_count} for p in self._pfs.values()]}


_registry: SkillProgramRegistry | None = None


def get_pf_registry() -> SkillProgramRegistry:
    global _registry
    if _registry is None:
        _registry = SkillProgramRegistry()
        _registry.register_builtins()
    return _registry
