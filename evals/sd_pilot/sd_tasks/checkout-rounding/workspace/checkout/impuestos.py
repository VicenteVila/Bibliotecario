"""Tipos de impuesto y cálculo de un impuesto sobre una base."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from checkout.redondeo import a_decimal, redondear

__all__ = ["EXENTO", "IVA_GENERAL", "IVA_REDUCIDO", "Impuesto", "importe_impuesto"]


@dataclass(frozen=True)
class Impuesto:
    """Una tasa aplicada al importe de cada línea (nombre + porcentaje)."""

    nombre: str
    tasa_pct: Decimal | str | int


IVA_GENERAL = Impuesto("IVA", Decimal(21))
IVA_REDUCIDO = Impuesto("IVA reducido", Decimal("10.5"))
EXENTO = Impuesto("EXENTO", Decimal(0))


def importe_impuesto(base: Decimal, impuesto: Impuesto, decimales: int = 2) -> Decimal:
    """Impuesto de UNA base, redondeado a ``decimales``."""
    tasa = a_decimal(impuesto.tasa_pct)
    return redondear(base * tasa / Decimal(100), decimales)
