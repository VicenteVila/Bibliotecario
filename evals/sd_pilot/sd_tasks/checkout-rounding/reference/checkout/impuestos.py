"""Tipos de impuesto y cálculo de un impuesto sobre una base ya redondeada."""

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

    def __post_init__(self) -> None:
        if not self.nombre:
            raise ValueError("nombre de impuesto vacio")
        tasa = a_decimal(self.tasa_pct)
        if tasa < 0:
            raise ValueError(f"tasa negativa: {tasa}")
        if tasa > 100:
            raise ValueError(f"tasa fuera de rango: {tasa}")
        object.__setattr__(self, "tasa_pct", tasa)


IVA_GENERAL = Impuesto("IVA", Decimal(21))
IVA_REDUCIDO = Impuesto("IVA reducido", Decimal("10.5"))
EXENTO = Impuesto("EXENTO", Decimal(0))


def importe_impuesto(base: Decimal, impuesto: Impuesto, decimales: int = 2) -> Decimal:
    """Impuesto de UNA base, redondeado half-up a ``decimales``."""
    if not isinstance(base, Decimal):
        raise TypeError(f"se espera Decimal: {type(base).__name__}")
    return redondear(base * impuesto.tasa_pct / Decimal(100), decimales)
