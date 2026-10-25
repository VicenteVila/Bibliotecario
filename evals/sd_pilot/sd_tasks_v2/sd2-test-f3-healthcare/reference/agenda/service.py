"""Fachada de agenda."""

from __future__ import annotations

from collections.abc import Sequence

from agenda.models import Cita, Resultado
from agenda.rules import asignar


class Agenda:
    def __init__(
        self, slots: Sequence[int], citas: Sequence[Cita]
    ) -> None:
        self._slots = tuple(slots)
        self._citas = tuple(citas)

    def asignar(self) -> Resultado:
        return asignar(self._slots, self._citas)

    def pendientes(self) -> int:
        return self.asignar().pendientes

    def procesar(self) -> Resultado:
        return self.asignar()
