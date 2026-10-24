"""Totales del checkout: subtotales, impuestos y total del pedido."""

from __future__ import annotations

from decimal import Decimal

from checkout.impuestos import Impuesto, importe_impuesto
from checkout.modelos import LineaPedido, Pedido
from checkout.redondeo import a_decimal, redondear

__all__ = [
    "desglose_impuestos",
    "importe_linea",
    "subtotal",
    "total_impuestos",
    "total_pedido",
]


def importe_linea(linea: LineaPedido, decimales: int = 2) -> Decimal:
    """Importe de la línea: ``cantidad * precio``."""
    cantidad = a_decimal(linea.cantidad)
    precio = a_decimal(linea.precio_unitario)
    return redondear(cantidad * precio, decimales)


def subtotal(pedido: Pedido) -> Decimal:
    """Subtotal del pedido."""
    bruto = Decimal(0)
    for linea in pedido.lineas:
        bruto += a_decimal(linea.cantidad) * a_decimal(linea.precio_unitario)
    return redondear(bruto, pedido.decimales)


def desglose_impuestos(pedido: Pedido) -> tuple[tuple[Impuesto, Decimal], ...]:
    """Importe de cada impuesto calculado sobre el subtotal del pedido."""
    base = subtotal(pedido)
    tramos = []
    for impuesto in pedido.impuestos:
        tramos.append((impuesto, importe_impuesto(base, impuesto, pedido.decimales)))
    return tuple(tramos)


def total_impuestos(pedido: Pedido) -> Decimal:
    """Suma de los impuestos del pedido."""
    acumulado = Decimal(0)
    for _, importe in desglose_impuestos(pedido):
        acumulado += importe
    return redondear(acumulado, pedido.decimales)


def total_pedido(pedido: Pedido) -> Decimal:
    """Total a pagar."""
    return redondear(subtotal(pedido) + total_impuestos(pedido), pedido.decimales)
