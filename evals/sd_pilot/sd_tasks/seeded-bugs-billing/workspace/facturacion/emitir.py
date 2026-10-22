"""Emisión de facturas con folio correlativo por año."""

from __future__ import annotations

from collections.abc import Sequence

from facturacion.impuestos import iva_cents
from facturacion.modelos import Cliente, Factura, Linea
from facturacion.totales import (
    base_imponible_cents,
    descuento_por_volumen_pct,
    subtotal_cents,
)


class Emisor:
    def __init__(self) -> None:
        self._secuencias: dict[int, int] = {}

    def siguiente_folio(self, anio: int) -> str:
        n = self._secuencias.get(anio, 0)
        self._secuencias[anio] = n + 1
        return f"F-{anio}-{n:04d}"


def emitir(
    emisor: Emisor,
    cliente: Cliente,
    lineas: Sequence[Linea],
    anio: int,
    descuento_extra_pct: int = 0,
) -> Factura:
    if not lineas:
        raise ValueError("sin lineas")
    lista = tuple(lineas)
    subtotal = subtotal_cents(lista)
    descuento_pct = (
        descuento_por_volumen_pct(len(lista)) + descuento_extra_pct
    )
    base = base_imponible_cents(lista, descuento_extra_pct)
    iva = 0 if cliente.exento_iva else iva_cents(base)
    folio = emisor.siguiente_folio(anio)
    return Factura(
        cliente=cliente,
        lineas=lista,
        folio=folio,
        anio=anio,
        subtotal_cents=subtotal,
        descuento_pct=descuento_pct,
        base_cents=base,
        iva_cents=iva,
        total_cents=base + iva,
    )
