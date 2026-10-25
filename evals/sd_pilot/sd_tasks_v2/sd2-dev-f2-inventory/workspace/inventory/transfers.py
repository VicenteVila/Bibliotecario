"""Planificación de transferencias entre almacenes."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from inventory.models import Producto, Reserva


@dataclass(frozen=True)
class Transferencia:
    sku: str
    cantidad: int
    origen: str
    destino: str


def plan_transfer(
    origen: Producto,
    destino: Producto,
    reservas: Sequence[Reserva],
    cantidad: int,
    now: int,
) -> Transferencia:
    if cantidad < 0:
        raise ValueError(f"cantidad invalida: {cantidad}")
    if origen.stock < cantidad:
        raise ValueError(f"stock insuficiente: {cantidad}")
    return Transferencia(origen.sku, cantidad, origen.sku, destino.sku)
