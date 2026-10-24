"""Tests públicos: formato del recibo."""

from decimal import Decimal

from checkout.impuestos import IVA_GENERAL
from checkout.modelos import LineaPedido, Pedido
from checkout.recibo import recibo


def test_recibo_rellena_hasta_dos_decimales():
    pedido = Pedido("P-002", (LineaPedido("TARIFA", 1, "10.5"),), ())
    texto = recibo(pedido)
    lineas = texto.splitlines()
    assert lineas[0] == "PEDIDO P-002"
    assert lineas[1] == "=" * len("PEDIDO P-002")
    assert "TARIFA x1 @10.50 = 10.50" in lineas
    assert "SUBTOTAL 10.50" in lineas


def test_recibo_total_con_iva():
    pedido = Pedido("P-003", (LineaPedido("LIBRO", 1, "19.99"),), (IVA_GENERAL,))
    lineas = recibo(pedido).splitlines()
    assert lineas[-2] == "IVA 21% 4.20"
    assert lineas[-1] == "TOTAL 24.19"
    assert Decimal(lineas[-1].split()[1]) == Decimal("24.19")
