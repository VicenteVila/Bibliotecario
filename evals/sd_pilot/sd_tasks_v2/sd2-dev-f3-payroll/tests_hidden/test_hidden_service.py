"""Tests ocultos de la fachada de nómina."""

import pytest
from nomina.models import Nomina
from nomina.service import CalculoNomina


def test_todo_cero():
    calculo = CalculoNomina(Nomina(0, 0, 0, 0))
    assert calculo.bruto() == 0
    assert calculo.impuesto() == 0
    assert calculo.neto() == 0


def test_extra_una_hora():
    assert CalculoNomina(Nomina(0, 1000, 1, 0)).bruto() == 1500


def test_impuesto_justo():
    assert CalculoNomina(Nomina(1, 100, 0, 10)).impuesto() == 10


def test_impuesto_medio_centavo():
    assert CalculoNomina(Nomina(1, 105, 0, 10)).impuesto() == 11


def test_tasa_cien():
    calculo = CalculoNomina(Nomina(1, 100, 0, 100))
    assert calculo.impuesto() == 100
    assert calculo.neto() == 0


def test_tarifa_negativa():
    with pytest.raises(ValueError, match="tarifa invalida"):
        CalculoNomina(Nomina(1, -1, 0, 10)).bruto()


def test_extra_negativa():
    with pytest.raises(ValueError, match="horas extra invalidas"):
        CalculoNomina(Nomina(1, 100, -1, 10)).bruto()


def test_tasa_negativa():
    with pytest.raises(ValueError, match="tasa invalida"):
        CalculoNomina(Nomina(1, 100, 0, -1)).bruto()


def test_tasa_mayor_cien():
    with pytest.raises(ValueError, match="tasa invalida"):
        CalculoNomina(Nomina(1, 100, 0, 101)).bruto()


def test_procesar_combinado():
    resultado = CalculoNomina(Nomina(40, 2000, 10, 20)).procesar()
    assert resultado.bruto == 110_000
    assert resultado.impuesto == 22_000
    assert resultado.neto == 88_000
