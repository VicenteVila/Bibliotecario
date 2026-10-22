"""Totales del checkout: redondeo POR LÍNEA antes de sumar y desglose de impuestos."""

from __future__ import annotations

from decimal import Decimal

from checkout.impuestos import Impuesto, importe_impuesto
from checkout.modelos import LineaPedido, Pedido
from checkout.redondeo import redondear

__all__ = [
    "desglose_impuestos",
    "importe_linea",
    "subtotal",
    "total_impuestos",
    "total_pedido",
]


def importe_linea(linea: LineaPedido, decimales: int = 2) -> Decimal:
    """Importe de la línea: ``cantidad * precio`` redondeado half-up AQUÍ."""
    return redondear(Decimal(linea.cantidad) * linea.precio_unitario, decimales)


def subtotal(pedido: Pedido) -> Decimal:
    """Suma de los importes de línea YA redondeados (nunca redondeo al final)."""
    acumulado = redondear(Decimal(0), pedido.decimales)
    for linea in pedido.lineas:
        acumulado += importe_linea(linea, pedido.decimales)
    return redondear(acumulado, pedido.decimales)


def desglose_impuestos(pedido: Pedido) -> tuple[tuple[Impuesto, Decimal], ...]:
    """Un tramo por impuesto configurado, en orden, con su importe total.

    Cada importe es la suma de lo que redondea CADA línea por separado
    (se redondea por línea y por impuesto, nunca sobre el subtotal).
    """
    tramos: list[tuple[Impuesto, Decimal]] = []
    for impuesto in pedido.impuestos:
        acumulado = redondear(Decimal(0), pedido.decimales)
        for linea in pedido.lineas:
            base = importe_linea(linea, pedido.decimales)
            acumulado += importe_impuesto(base, impuesto, pedido.decimales)
        tramos.append((impuesto, redondear(acumulado, pedido.decimales)))
    return tuple(tramos)


def total_impuestos(pedido: Pedido) -> Decimal:
    """Suma de todos los tramos de impuestos (ya redondeados uno a uno)."""
    acumulado = redondear(Decimal(0), pedido.decimales)
    for _, importe in desglose_impuestos(pedido):
        acumulado += importe
    return redondear(acumulado, pedido.decimales)


def total_pedido(pedido: Pedido) -> Decimal:
    """``subtotal + impuestos``, con los dos sumandos ya redondeados."""
    return redondear(subtotal(pedido) + total_impuestos(pedido), pedido.decimales)
