"""Motor de transiciones del workflow."""
from __future__ import annotations

from approvalflow.guards import GUARDS
from approvalflow.states import INITIAL, TERMINALS
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
        """Aplica un evento; errores -> sin cambio de estado."""
        if not isinstance(event, str):
            raise TypeError("event must be str")
        if ctx is not None and not isinstance(ctx, dict):
            raise TypeError("ctx must be dict or None")
        if self._state in TERMINALS:
            raise IllegalTransition(f"terminal: {self._state}")
        key = (self._state, event)
        transicion = TRANSITIONS.get(key)
        if transicion is None:
            raise IllegalTransition(f"illegal: {self._state} -{event}-> ?")
        destino, guard_id = transicion
        if guard_id is not None:
            GUARDS[guard_id](ctx if ctx is not None else {})
        self._state = destino
        return destino
