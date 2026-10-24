"""Cálculo del stock disponible."""

from __future__ import annotations

from collections.abc import Sequence

from inventory.models import Producto, Reserva


def available_stock(
    producto: Producto, reservas: Sequence[Reserva], now: int
) -> int:
    total = producto.stock
    for reserva in reservas:
        if reserva.sku != producto.sku:
            continue
        if reserva.status != "active":
            continue
        total -= reserva.cantidad
    return total
