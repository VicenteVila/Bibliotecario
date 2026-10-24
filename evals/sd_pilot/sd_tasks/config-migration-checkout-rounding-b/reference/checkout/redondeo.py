"""Redondeo monetario exacto con ``Decimal`` (half-up) y conversión de importes.

Regla de la casa: el dinero NUNCA pasa por ``float`` ni por ``round()`` de
Python (redondeo bancario). Todo pasa por :func:`redondear`, que usa
``decimal.ROUND_HALF_UP`` (empates hacia fuera de cero).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

__all__ = ["a_decimal", "redondear"]


def a_decimal(valor: object) -> Decimal:
    """Convierte un importe a ``Decimal`` sin pasar nunca por ``float``."""
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, bool):
        raise TypeError(f"tipo no soportado: {type(valor).__name__}")
    if isinstance(valor, float):
        raise TypeError(f"float prohibido para dinero: {type(valor).__name__}")
    if isinstance(valor, int):
        return Decimal(valor)
    if isinstance(valor, str):
        try:
            return Decimal(valor)
        except InvalidOperation:
            raise ValueError(f"importe no valido: {valor}") from None
    raise TypeError(f"tipo no soportado: {type(valor).__name__}")


def _exponencial(decimales: int) -> Decimal:
    if not isinstance(decimales, int) or isinstance(decimales, bool):
        raise TypeError(f"decimales no entero: {type(decimales).__name__}")
    if decimales < 0:
        raise ValueError(f"decimales invalidos: {decimales}")
    return Decimal(1).scaleb(-decimales)


def redondear(valor: Decimal, decimales: int = 2) -> Decimal:
    """Redondeo monetario **half-up** (empates hacia fuera de cero)."""
    if not isinstance(valor, Decimal):
        raise TypeError(f"se espera Decimal: {type(valor).__name__}")
    return valor.quantize(_exponencial(decimales), rounding=ROUND_HALF_UP)
