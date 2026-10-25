"""Reglas de cotización logística."""

from __future__ import annotations

from logistica.models import Envio


def _validate(envio: Envio) -> None:
    if envio.peso_kg < 0:
        raise ValueError("peso invalido")
    if envio.volumen_l < 0:
        raise ValueError("volumen invalido")
    if envio.distancia_km < 0:
        raise ValueError("distancia invalida")


def base(envio: Envio) -> int:
    _validate(envio)
    return (
        500
        + envio.peso_kg * 20
        + envio.volumen_l * 2
        + envio.distancia_km * 10
    )


def recargos(envio: Envio, base_cents: int) -> int:
    if envio.express:
        return base_cents // 2
    return 0


def total(base_cents: int, recargos_cents: int) -> int:
    return max(1000, base_cents + recargos_cents)
