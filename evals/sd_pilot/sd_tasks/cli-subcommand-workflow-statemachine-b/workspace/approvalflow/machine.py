"""Motor de transiciones del workflow (versión inicial naive)."""
from __future__ import annotations

from approvalflow.states import INITIAL
from approvalflow.transitions import TRANSITIONS


class IllegalTransition(Exception):
    """Transición no permitida desde el estado actual."""


class StateMachine:
    """Máquina de estados del workflow de aprobaciones."""

    def __init__(self) -> None:
        self._state = INITIAL

    @property
    def state(self) -> str:
        return self._state

    def apply(self, event: str, ctx: dict | None = None) -> str:
        """Aplica un evento. Versión inicial: ignora guardas y terminales."""
        key = (self._state, event)
        if key not in TRANSITIONS:
            raise IllegalTransition(f"illegal: {self._state} -{event}-> ?")
        destino, _guard_id = TRANSITIONS[key]
        self._state = destino
        return destino
