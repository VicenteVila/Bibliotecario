"""Tests ocultos: total del pedido como suma de líneas e impuestos ya redondeados."""

from decimal import Decimal

from checkout.impuestos import IVA_GENERAL
from checkout.modelos import LineaPedido, Pedido
from checkout.totales import subtotal, total_impuestos, total_pedido


def test_total_es_suma_de_lineas_redondeadas_mas_impuestos():
    lineas = (
        LineaPedido("a", 1, "1.005"),
        LineaPedido("b", 1, "1.005"),
        LineaPedido("c", 1, "1.005"),
    )
    pedido = Pedido("P", lineas, (IVA_GENERAL,))
    assert subtotal(pedido) == Decimal("3.03")
    assert total_impuestos(pedido) == Decimal("0.63")
    assert total_pedido(pedido) == Decimal("3.66")
    assert total_pedido(pedido) == subtotal(pedido) + total_impuestos(pedido)


def test_total_con_cuatro_decimales():
    lineas = (LineaPedido("a", 1, "1.00005"), LineaPedido("b", 3, "0.00015"))
    pedido = Pedido("P", lineas, (IVA_GENERAL,), decimales=4)
    assert subtotal(pedido) == Decimal("1.0006")
    assert total_impuestos(pedido) == Decimal("0.2101")
    assert total_pedido(pedido) == Decimal("1.2107")


def test_total_sin_impuestos():
    pedido = Pedido("P", (LineaPedido("a", 2, "0.005"),), ())
    assert total_pedido(pedido) == Decimal("0.01")
    assert total_pedido(pedido) == subtotal(pedido)


def test_total_con_devolucion_y_iva():
    pedido = Pedido("P", (LineaPedido("dev", -1, "10.00"),), (IVA_GENERAL,))
    assert subtotal(pedido) == Decimal("-10.00")
    assert total_impuestos(pedido) == Decimal("-2.10")
    assert total_pedido(pedido) == Decimal("-12.10")


def test_total_de_pedido_vacio():
    pedido = Pedido("P", (), ())
    assert total_pedido(pedido) == Decimal("0.00")


def test_total_con_linea_a_cero_e_iva():
    pedido = Pedido("P", (LineaPedido("bon", 0, "19.99"),), (IVA_GENERAL,))
    assert subtotal(pedido) == Decimal("0.00")
    assert total_impuestos(pedido) == Decimal("0.00")
    assert total_pedido(pedido) == Decimal("0.00")
