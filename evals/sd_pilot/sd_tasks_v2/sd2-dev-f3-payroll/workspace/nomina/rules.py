"""Reglas de cálculo de nómina."""

from __future__ import annotations

from nomina.models import Nomina


def _validate(nomina: Nomina) -> None:
    if nomina.horas < 0:
        raise ValueError("horas invalidas")
    if nomina.tarifa_cents < 0:
        raise ValueError("tarifa invalida")
    if nomina.horas_extra < 0:
        raise ValueError("horas extra invalidas")
    if not 0 <= nomina.tasa_pct <= 100:
        raise ValueError("tasa invalida")


def bruto(nomina: Nomina) -> int:
    _validate(nomina)
    extra = nomina.horas_extra * nomina.tarifa_cents * 3 // 2
    return nomina.horas * nomina.tarifa_cents + extra


def impuesto(bruto_cents: int, tasa_pct: int) -> int:
    return (bruto_cents * tasa_pct + 50) // 100


def neto(bruto_cents: int, impuesto_cents: int) -> int:
    return bruto_cents - impuesto_cents
