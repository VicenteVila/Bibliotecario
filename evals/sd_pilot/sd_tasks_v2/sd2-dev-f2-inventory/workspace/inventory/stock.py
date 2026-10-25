"""Cálculo del stock disponible."""

from __future__ import annotations

from collections.abc import Sequence

from inventory.models import Producto, Reserva
from inventory.reservations import is_expired


def available_stock(
    producto: Producto, reservas: Sequence[Reserva], now: int
) -> int:
    total = producto.stock
    for reserva in reservas:
        if reserva.sku != producto.sku:
            continue
        if reserva.status != "active":
            continue
        if is_expired(reserva, now):
            continue
        total -= reserva.cantidad
    return total
