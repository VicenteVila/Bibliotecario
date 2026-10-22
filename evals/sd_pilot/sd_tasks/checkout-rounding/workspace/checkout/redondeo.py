"""Redondeo de importes del checkout (versión inicial, aún no fiable)."""

from __future__ import annotations

from decimal import Decimal

__all__ = ["a_decimal", "redondear"]


def a_decimal(valor: object) -> Decimal:
    """Convierte cualquier número de entrada a ``Decimal``."""
    if isinstance(valor, Decimal):
        return valor
    try:
        return Decimal(str(valor))
    except Exception:
        raise ValueError(f"importe no valido: {valor}") from None


def redondear(valor: Decimal, decimales: int = 2) -> Decimal:
    """Redondea al número de decimales indicado."""
    if decimales < 0:
        raise ValueError(f"decimales invalidos: {decimales}")
    return Decimal(str(round(float(valor), decimales)))
