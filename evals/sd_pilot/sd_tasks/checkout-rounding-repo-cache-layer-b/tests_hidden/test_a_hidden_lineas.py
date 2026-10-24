"""Tests ocultos: importe por línea, subtotal y validaciones de modelos."""

from decimal import Decimal

import pytest
from checkout.modelos import LineaPedido, Pedido
from checkout.totales import importe_linea, subtotal


def test_importe_linea_basico():
    assert importe_linea(LineaPedido("libro", 3, "19.99")) == Decimal("59.97")
    assert importe_linea(LineaPedido("libro", 1, "19.99"), 4) == Decimal("19.9900")


def test_importe_linea_empate_en_cuatro_decimales():
    assert importe_linea(LineaPedido("x", 1, "0.00025"), 4) == Decimal("0.0003")


def test_importe_linea_cantidad_cero():
    assert importe_linea(LineaPedido("nada", 0, "19.99")) == Decimal("0.00")


def test_importe_linea_devolucion_negativa():
    assert importe_linea(LineaPedido("dev", -2, "19.99")) == Decimal("-39.98")
    assert importe_linea(LineaPedido("dev", -1, "1.005")) == Decimal("-1.01")


def test_importe_linea_rechaza_precio_float():
    with pytest.raises(TypeError, match="float prohibido para dinero"):
        LineaPedido("x", 1, 19.99)


def test_importe_linea_rechaza_cantidad_no_entera():
    with pytest.raises(TypeError, match="cantidad no entera"):
        LineaPedido("x", "2", "1.00")


def test_linea_con_descripcion_vacia():
    with pytest.raises(ValueError, match="descripcion vacia"):
        LineaPedido("", 1, "1.00")


def test_linea_con_precio_negativo():
    with pytest.raises(ValueError, match="precio negativo"):
        LineaPedido("x", 1, "-1.00")


def test_subtotal_suma_importes_ya_redondeados():
    pedido = Pedido(
        "P",
        (LineaPedido("a", 1, "1.005"), LineaPedido("b", 1, "1.005")),
        (),
    )
    assert subtotal(pedido) == Decimal("2.02")


def test_subtotal_redondea_cada_linea_a_cuatro_decimales():
    lineas = tuple(LineaPedido("x", 1, "0.00005") for _ in range(3))
    pedido = Pedido("P", lineas, (), decimales=4)
    assert subtotal(pedido) == Decimal("0.0003")


def test_subtotal_vacio_da_cero():
    pedido = Pedido("P", (), ())
    assert subtotal(pedido) == Decimal("0.00")


def test_pedido_valida_identificador_y_decimales():
    with pytest.raises(ValueError, match="identificador vacio"):
        Pedido("", (), ())
    with pytest.raises(ValueError, match="decimales invalidos"):
        Pedido("P", (), (), decimales=-1)


def test_pedido_con_decimales_cero():
    pedido = Pedido("P", (LineaPedido("a", 1, "2.5"),), (), decimales=0)
    assert importe_linea(pedido.lineas[0], 0) == Decimal(3)
    assert subtotal(pedido) == Decimal(3)
