"""Fachada de reservas pendiente de implementar."""

from __future__ import annotations

from collections.abc import Sequence

from reservas.models import Reserva, Resultado


class Reservas:
    def __init__(
        self,
        capacidad: int,
        reservas: Sequence[Reserva],
        now: int,
    ) -> None:
        self._capacidad = capacidad
        self._reservas = tuple(reservas)
        self._now = now

    def disponible(self) -> int:
        raise NotImplementedError

    def caducadas(self) -> int:
        raise NotImplementedError

    def alerta(self) -> bool:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
