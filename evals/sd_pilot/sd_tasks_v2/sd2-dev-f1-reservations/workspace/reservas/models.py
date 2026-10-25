"""Modelos de reservas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reserva:
    reserva_id: str
    cantidad: int
    created_at: int
    ttl_seconds: int
    status: str = "active"


@dataclass(frozen=True)
class Resultado:
    disponible: int
    caducadas: int
    alerta: bool
