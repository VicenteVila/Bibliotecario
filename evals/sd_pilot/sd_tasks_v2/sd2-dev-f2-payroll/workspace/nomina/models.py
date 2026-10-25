"""Modelos de nómina."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Nomina:
    horas: int
    tarifa_cents: int
    horas_extra: int
    tasa_pct: int


@dataclass(frozen=True)
class Resultado:
    bruto: int
    impuesto: int
    neto: int
