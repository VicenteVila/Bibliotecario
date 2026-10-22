"""Tests ocultos: formato exacto del recibo, de importes y de tasas."""

from decimal import Decimal

import pytest
from checkout.impuestos import EXENTO, IVA_GENERAL, IVA_REDUCIDO
from checkout.modelos import LineaPedido, Pedido
from checkout.recibo import formato_importe, formato_tasa, recibo


def test_formato_importe_rellena_hasta_los_decimales():
    assert formato_importe(Decimal("19.5")) == "19.50"
    assert formato_importe(Decimal(10), 4) == "10.0000"
    assert formato_importe(Decimal(0)) == "0.00"
    assert formato_importe(Decimal("-39.987")) == "-39.99"


def test_formato_importe_normaliza_el_cero_negativo():
    assert formato_importe(Decimal("-0.004")) == "0.00"
    assert formato_importe(Decimal("-0.00004"), 4) == "0.0000"


def test_formato_importe_redondea_half_up():
    assert formato_importe(Decimal("2.675")) == "2.68"
    assert formato_importe(Decimal("1.00005"), 4) == "1.0001"
    assert formato_importe(Decimal("2.5"), 0) == "3"


def test_formato_tasa_sin_ceros_sobrantes():
    assert formato_tasa(Decimal(21)) == "21"
    assert formato_tasa(Decimal("10.50")) == "10.5"
    assert formato_tasa("10.5") == "10.5"
    assert formato_tasa(0) == "0"


def test_formato_tasa_rechaza_float():
    with pytest.raises(TypeError, match="float prohibido para dinero"):
        formato_tasa(21.0)


def test_recibo_exacto_con_iva():
    pedido = Pedido(
        "P-001",
        (LineaPedido("LIBRO", 1, "19.99"), LineaPedido("CAJA", 3, "2.50")),
        (IVA_GENERAL,),
    )
    esperado = (
        "PEDIDO P-001\n"
        "============\n"
        "LIBRO x1 @19.99 = 19.99\n"
        "CAJA x3 @2.50 = 7.50\n"
        "SUBTOTAL 27.49\n"
        "IVA 21% 5.78\n"
        "TOTAL 33.27"
    )
    assert recibo(pedido) == esperado


def test_recibo_exacto_con_dos_tasas():
    pedido = Pedido(
        "P-002",
        (LineaPedido("SERVICIO", 1, "100.00"),),
        (IVA_GENERAL, IVA_REDUCIDO),
    )
    esperado = (
        "PEDIDO P-002\n"
        "============\n"
        "SERVICIO x1 @100.00 = 100.00\n"
        "SUBTOTAL 100.00\n"
        "IVA 21% 21.00\n"
        "IVA reducido 10.5% 10.50\n"
        "TOTAL 131.50"
    )
    assert recibo(pedido) == esperado


def test_recibo_exacto_a_cuatro_decimales():
    pedido = Pedido(
        "P-003",
        (LineaPedido("SERIE", 2, "1.00005"),),
        (IVA_GENERAL,),
        decimales=4,
    )
    esperado = (
        "PEDIDO P-003\n"
        "============\n"
        "SERIE x2 @1.0001 = 2.0001\n"
        "SUBTOTAL 2.0001\n"
        "IVA 21% 0.4200\n"
        "TOTAL 2.4201"
    )
    assert recibo(pedido) == esperado


def test_recibo_muestra_precio_redondeado_y_calcula_sin_redondearlo():
    pedido = Pedido("P-004", (LineaPedido("TARIFA", 4, "0.005"),), ())
    esperado = (
        "PEDIDO P-004\n"
        "============\n"
        "TARIFA x4 @0.01 = 0.02\n"
        "SUBTOTAL 0.02\n"
        "TOTAL 0.02"
    )
    assert recibo(pedido) == esperado


def test_recibo_de_devolucion_negativa():
    pedido = Pedido("P-005", (LineaPedido("DEV", -2, "19.99"),), (IVA_GENERAL,))
    esperado = (
        "PEDIDO P-005\n"
        "============\n"
        "DEV x-2 @19.99 = -39.98\n"
        "SUBTOTAL -39.98\n"
        "IVA 21% -8.40\n"
        "TOTAL -48.38"
    )
    assert recibo(pedido) == esperado


def test_recibo_linea_a_cero_y_tasa_exenta():
    pedido = Pedido("P-006", (LineaPedido("BON", 0, "19.99"),), (EXENTO,))
    esperado = (
        "PEDIDO P-006\n"
        "============\n"
        "BON x0 @19.99 = 0.00\n"
        "SUBTOTAL 0.00\n"
        "EXENTO 0% 0.00\n"
        "TOTAL 0.00"
    )
    assert recibo(pedido) == esperado


def test_recibo_sin_impuestos():
    pedido = Pedido("P-007", (LineaPedido("a", 1, "10.50"),), ())
    assert recibo(pedido).splitlines() == [
        "PEDIDO P-007",
        "============",
        "a x1 @10.50 = 10.50",
        "SUBTOTAL 10.50",
        "TOTAL 10.50",
    ]


def test_recibo_sin_lineas_lanza_error():
    with pytest.raises(ValueError, match="sin lineas"):
        recibo(Pedido("P-008", (), (IVA_GENERAL,)))


def test_recibo_sin_salto_de_linea_final():
    pedido = Pedido("P-009", (LineaPedido("a", 1, "1.00"),), (IVA_GENERAL,))
    texto = recibo(pedido)
    assert not texto.endswith("\n")
    assert texto.count("\n") == 5
