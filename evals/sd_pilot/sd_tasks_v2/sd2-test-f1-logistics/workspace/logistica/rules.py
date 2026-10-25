"""Reglas de cotización logística."""

from __future__ import annotations

from logistica.models import Envio


def base(envio: Envio) -> int:
    return (
        500
        + envio.peso_kg * 20
        + envio.volumen_l * 2
        + envio.distancia_km * 10
    )


def recargos(envio: Envio, base_cents: int) -> int:
    if envio.express:
        return 500
    return 0


def total(base_cents: int, recargos_cents: int) -> int:
    return base_cents + recargos_cents
