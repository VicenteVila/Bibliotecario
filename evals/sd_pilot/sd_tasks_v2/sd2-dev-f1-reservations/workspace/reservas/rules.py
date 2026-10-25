"""Reglas de capacidad y caducidad."""

from __future__ import annotations

from collections.abc import Sequence

from reservas.models import Reserva


def is_expired(reserva: Reserva, now: int) -> bool:
    return now - reserva.created_at > reserva.ttl_seconds


def disponible(
    capacidad: int, reservas: Sequence[Reserva], now: int
) -> int:
    total = capacidad
    for reserva in reservas:
        if reserva.status == "active":
            total -= reserva.cantidad
    return total


def caducadas(reservas: Sequence[Reserva], now: int) -> int:
    return sum(
        1
        for reserva in reservas
        if reserva.status == "active" and is_expired(reserva, now)
    )


def alerta(disponible_actual: int) -> bool:
    return disponible_actual < 1
