"""Ciclo de vida de las reservas."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from inventory.models import Reserva


def is_expired(reserva: Reserva, now: int) -> bool:
    return now - reserva.created_at > reserva.ttl_seconds


def release_expired(
    reservas: Sequence[Reserva], now: int
) -> tuple[Reserva, ...]:
    resultado: list[Reserva] = []
    for reserva in reservas:
        if reserva.status == "active" and is_expired(reserva, now):
            resultado.append(replace(reserva, status="expired"))
        else:
            resultado.append(reserva)
    return tuple(resultado)
