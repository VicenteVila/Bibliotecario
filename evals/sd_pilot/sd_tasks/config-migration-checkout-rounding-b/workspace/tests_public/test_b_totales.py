"""Tests públicos: importes por línea, subtotales y totales."""

from decimal import Decimal

from checkout.impuestos import IVA_GENERAL
from checkout.modelos import LineaPedido, Pedido
from checkout.totales import importe_linea, subtotal, total_impuestos, total_pedido


def test_importes_de_linea_basicos():
    assert importe_linea(LineaPedido("LIBRO", 1, "19.99")) == Decimal("19.99")
    assert importe_linea(LineaPedido("CAJA", 3, "2.50")) == Decimal("7.50")


def test_pedido_completo_con_iva():
    pedido = Pedido(
        "P-001",
        (LineaPedido("LIBRO", 1, "19.99"), LineaPedido("CAJA", 3, "2.50")),
        (IVA_GENERAL,),
    )
    assert subtotal(pedido) == Decimal("27.49")
    assert total_impuestos(pedido) == Decimal("5.78")
    assert total_pedido(pedido) == Decimal("33.27")


def test_linea_a_cero_y_devolucion():
    assert importe_linea(LineaPedido("BON", 0, "19.99")) == Decimal("0.00")
    assert importe_linea(LineaPedido("DEV", -2, "19.99")) == Decimal("-39.98")
