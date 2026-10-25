"""Fachada de inventario."""

from __future__ import annotations

from collections.abc import Iterable

from inventory.alerts import needs_reorder
from inventory.models import Producto, Reserva
from inventory.reservations import release_expired
from inventory.stock import available_stock


class Inventario:
    def __init__(
        self,
        productos: dict[str, Producto],
        reservas: Iterable[Reserva],
    ) -> None:
        self._productos = dict(productos)
        self._reservas = list(reservas)

    def disponible(self, sku: str, now: int) -> int:
        return available_stock(self._productos[sku], self._reservas, now)

    def alerta(self, sku: str, now: int) -> bool:
        return needs_reorder(self._productos[sku], self._reservas, now)

    def liberar(self, now: int) -> int:
        antes = sum(
            1 for r in self._reservas if r.status == "active"
        )
        self._reservas = list(release_expired(self._reservas, now))
        despues = sum(
            1 for r in self._reservas if r.status == "active"
        )
        return antes - despues

    def reservas_actuales(self) -> tuple[Reserva, ...]:
        return tuple(self._reservas)
