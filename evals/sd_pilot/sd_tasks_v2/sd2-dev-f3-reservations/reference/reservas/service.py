"""Fachada de reservas."""

from __future__ import annotations

from collections.abc import Sequence

from reservas.models import Reserva, Resultado
from reservas.rules import alerta, caducadas, disponible


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
        return disponible(self._capacidad, self._reservas, self._now)

    def caducadas(self) -> int:
        return caducadas(self._reservas, self._now)

    def alerta(self) -> bool:
        return alerta(self.disponible())

    def procesar(self) -> Resultado:
        return Resultado(
            disponible=self.disponible(),
            caducadas=self.caducadas(),
            alerta=self.alerta(),
        )
