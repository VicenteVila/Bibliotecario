"""Fachada de agenda pendiente de implementar."""

from __future__ import annotations

from collections.abc import Sequence

from agenda.models import Cita, Resultado


class Agenda:
    def __init__(
        self, slots: Sequence[int], citas: Sequence[Cita]
    ) -> None:
        self._slots = tuple(slots)
        self._citas = tuple(citas)

    def asignar(self) -> Resultado:
        raise NotImplementedError

    def pendientes(self) -> int:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
