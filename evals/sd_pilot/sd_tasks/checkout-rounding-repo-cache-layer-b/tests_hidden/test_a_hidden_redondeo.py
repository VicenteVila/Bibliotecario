"""Tests ocultos: redondeo monetario half-up y conversión de importes."""

from decimal import Decimal

import pytest
from checkout.redondeo import a_decimal, redondear


def test_a_decimal_acepta_cadena_entero_y_decimal():
    assert a_decimal("19.99") == Decimal("19.99")
    assert a_decimal(5) == Decimal(5)
    assert a_decimal(Decimal("7.5")) == Decimal("7.5")


def test_a_decimal_rechaza_float():
    with pytest.raises(TypeError, match="float prohibido para dinero"):
        a_decimal(19.99)


def test_a_decimal_cadena_no_numerica():
    with pytest.raises(ValueError, match="importe no valido"):
        a_decimal("no-numero")


def test_a_decimal_tipo_no_soportado():
    with pytest.raises(TypeError, match="tipo no soportado"):
        a_decimal(None)


def test_redondear_empates_hacia_fuera_de_cero():
    assert redondear(Decimal("1.005"), 2) == Decimal("1.01")
    assert redondear(Decimal("2.675"), 2) == Decimal("2.68")
    assert redondear(Decimal("1.00005"), 4) == Decimal("1.0001")
    assert redondear(Decimal("2.5"), 0) == Decimal(3)


def test_redondear_valores_fuera_de_empate():
    assert redondear(Decimal("1.004"), 2) == Decimal("1.00")
    assert redondear(Decimal("1.00004"), 4) == Decimal("1.0000")
    assert redondear(Decimal(10), 2) == Decimal("10.00")


def test_redondear_negativos_en_empate_fuera_de_cero():
    assert redondear(Decimal("-1.005"), 2) == Decimal("-1.01")
    assert redondear(Decimal("-2.5"), 0) == Decimal(-3)


def test_redondear_cero_y_casi_cero():
    assert redondear(Decimal(0), 2) == Decimal("0.00")
    assert redondear(Decimal("-0.004"), 2) == Decimal("0.00")


def test_redondear_decimales_invalidos():
    with pytest.raises(ValueError, match="decimales invalidos"):
        redondear(Decimal(1), -1)


def test_redondear_exige_decimal():
    with pytest.raises(TypeError, match="se espera Decimal"):
        redondear(1.5, 2)
