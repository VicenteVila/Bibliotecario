"""Impuestos del pipeline de facturación. Corrige el redondeo (half-up)."""

from __future__ import annotations

TASA_IVA_DEFECTO = 21


def iva_cents(base_cents: int, tasa_pct: int = TASA_IVA_DEFECTO) -> int:
    return (base_cents * tasa_pct + 50) // 100
