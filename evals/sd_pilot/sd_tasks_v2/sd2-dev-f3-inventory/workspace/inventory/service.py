"""Fachada de inventario pendiente de implementar."""

from __future__ import annotations

from collections.abc import Iterable

from inventory.models import Producto, Reserva


class Inventario:
    def __init__(
        self,
        productos: dict[str, Producto],
        reservas: Iterable[Reserva],
    ) -> None:
        self._productos = dict(productos)
        self._reservas = list(reservas)

    def disponible(self, sku: str, now: int) -> int:
        raise NotImplementedError

    def alerta(self, sku: str, now: int) -> bool:
        raise NotImplementedError

    def liberar(self, now: int) -> int:
        raise NotImplementedError

    def reservas_actuales(self) -> tuple[Reserva, ...]:
        raise NotImplementedError
