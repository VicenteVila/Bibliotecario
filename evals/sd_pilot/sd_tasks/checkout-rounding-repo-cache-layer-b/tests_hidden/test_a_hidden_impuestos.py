"""Tests ocultos: impuestos combinados, validación de tasas y redondeo por línea."""

from decimal import Decimal

import pytest
from checkout.impuestos import (
    EXENTO,
    IVA_GENERAL,
    IVA_REDUCIDO,
    Impuesto,
    importe_impuesto,
)
from checkout.modelos import LineaPedido, Pedido
from checkout.totales import desglose_impuestos, total_impuestos


def test_importe_impuesto_tasas_fijas():
    assert importe_impuesto(Decimal(100), IVA_GENERAL) == Decimal("21.00")
    assert importe_impuesto(Decimal(100), IVA_REDUCIDO) == Decimal("10.50")
    assert importe_impuesto(Decimal(0), IVA_GENERAL) == Decimal("0.00")


def test_importe_impuesto_tasa_cero():
    assert importe_impuesto(Decimal(100), EXENTO) == Decimal("0.00")


def test_importe_impuesto_empate_half_up():
    assert importe_impuesto(Decimal("0.25"), Impuesto("t", "2")) == Decimal("0.01")
    assert importe_impuesto(Decimal("-0.25"), Impuesto("t", "2")) == Decimal("-0.01")


def test_importe_impuesto_cuatro_decimales():
    assert importe_impuesto(Decimal("1.005"), IVA_GENERAL, 4) == Decimal("0.2111")


def test_importe_impuesto_exige_decimal():
    with pytest.raises(TypeError, match="se espera Decimal"):
        importe_impuesto(100.0, IVA_GENERAL)


def test_impuesto_rechaza_tasa_float():
    with pytest.raises(TypeError, match="float prohibido para dinero"):
        Impuesto("IVA", 21.0)


def test_impuesto_validaciones():
    with pytest.raises(ValueError, match="nombre de impuesto vacio"):
        Impuesto("", "21")
    with pytest.raises(ValueError, match="tasa negativa"):
        Impuesto("mala", "-1")
    with pytest.raises(ValueError, match="tasa fuera de rango"):
        Impuesto("mala", "150")


def test_impuestos_predefinidos():
    assert IVA_GENERAL.nombre == "IVA"
    assert IVA_GENERAL.tasa_pct == Decimal(21)
    assert IVA_REDUCIDO.nombre == "IVA reducido"
    assert IVA_REDUCIDO.tasa_pct == Decimal("10.5")
    assert EXENTO.tasa_pct == Decimal(0)


def test_impuestos_se_calculan_y_redondean_por_linea():
    pedido = Pedido(
        "P",
        (LineaPedido("a", 1, "0.05"), LineaPedido("b", 1, "0.05")),
        (Impuesto("A", "10"),),
    )
    assert desglose_impuestos(pedido)[0][1] == Decimal("0.02")
    assert total_impuestos(pedido) == Decimal("0.02")


def test_dos_tasas_combinadas_en_una_linea():
    lineas = (LineaPedido("a", 1, "0.05"),)
    impuestos = (Impuesto("A", "10"), Impuesto("B", "21"))
    pedido = Pedido("P", lineas, impuestos)
    assert desglose_impuestos(pedido) == (
        (impuestos[0], Decimal("0.01")),
        (impuestos[1], Decimal("0.01")),
    )
    assert total_impuestos(pedido) == Decimal("0.02")


def test_desglose_respeta_el_orden_configurado():
    pedido = Pedido(
        "P",
        (LineaPedido("s", 1, "100.00"),),
        (IVA_REDUCIDO, IVA_GENERAL, EXENTO),
    )
    assert [imp.nombre for imp, _ in desglose_impuestos(pedido)] == [
        "IVA reducido",
        "IVA",
        "EXENTO",
    ]
    assert [importe for _, importe in desglose_impuestos(pedido)] == [
        Decimal("10.50"),
        Decimal("21.00"),
        Decimal("0.00"),
    ]


def test_pedido_sin_impuestos_no_cobra_nada():
    pedido = Pedido("P", (LineaPedido("a", 1, "10.00"),), ())
    assert desglose_impuestos(pedido) == ()
    assert total_impuestos(pedido) == Decimal("0.00")
