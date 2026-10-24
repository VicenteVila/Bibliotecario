"""Alertas de reposición."""

from __future__ import annotations

from collections.abc import Sequence

from inventory.models import Producto, Reserva
from inventory.stock import available_stock


def needs_reorder(
    producto: Producto, reservas: Sequence[Reserva], now: int
) -> bool:
    return available_stock(producto, reservas, now) < producto.reorder_level
