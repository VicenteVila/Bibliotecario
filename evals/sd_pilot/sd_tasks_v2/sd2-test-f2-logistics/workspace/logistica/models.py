"""Modelos de logística."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Envio:
    peso_kg: int
    volumen_l: int
    distancia_km: int
    express: bool = False


@dataclass(frozen=True)
class Resultado:
    base: int
    recargos: int
    total: int
