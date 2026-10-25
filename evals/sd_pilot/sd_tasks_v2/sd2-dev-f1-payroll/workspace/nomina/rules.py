"""Reglas de cálculo de nómina."""

from __future__ import annotations

from nomina.models import Nomina


def bruto(nomina: Nomina) -> int:
    return (
        nomina.horas * nomina.tarifa_cents
        + nomina.horas_extra * nomina.tarifa_cents * 2
    )


def impuesto(bruto_cents: int, tasa_pct: int) -> int:
    return bruto_cents * tasa_pct // 100


def neto(bruto_cents: int, impuesto_cents: int) -> int:
    return bruto_cents - impuesto_cents
