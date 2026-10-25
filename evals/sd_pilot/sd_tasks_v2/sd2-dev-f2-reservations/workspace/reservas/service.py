"""Servicio de reservas pendiente de completar."""

from __future__ import annotations

from collections.abc import Sequence

from reservas.models import Reserva, Resultado


def procesar(
    capacidad: int, reservas: Sequence[Reserva], now: int
) -> Resultado:
    total = capacidad
    for reserva in reservas:
        total -= reserva.cantidad
    return Resultado(total, 0, total < 1)
