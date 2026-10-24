"""Totales del pipeline de facturación. Corrige los umbrales incluyentes."""

from __future__ import annotations

from collections.abc import Sequence

from facturacion.modelos import Linea


def subtotal_cents(lineas: Sequence[Linea]) -> int:
    total = 0
    for linea in lineas:
        if linea.cantidad < 1:
            raise ValueError(f"cantidad no positiva: {linea.cantidad}")
        if linea.precio_unit_cents < 0:
            raise ValueError(f"precio negativo: {linea.precio_unit_cents}")
        total += linea.cantidad * linea.precio_unit_cents
    return total


def descuento_por_volumen_pct(num_lineas: int) -> int:
    if num_lineas >= 10:
        return 10
    if num_lineas >= 5:
        return 5
    return 0


def descuento_cents(monto: int, pct: int) -> int:
    return (monto * pct + 50) // 100


def base_imponible_cents(
    lineas: Sequence[Linea], descuento_extra_pct: int = 0
) -> int:
    subtotal = subtotal_cents(lineas)
    pct_total = descuento_por_volumen_pct(len(lineas)) + descuento_extra_pct
    if pct_total > 100:
        raise ValueError(f"descuento total invalido: {pct_total}")
    return subtotal - descuento_cents(subtotal, pct_total)
