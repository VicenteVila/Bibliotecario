"""Tests ocultos de nómina."""

import pytest
from nomina.models import Nomina
from nomina.service import procesar


def test_extra_una_hora():
    assert procesar(Nomina(0, 1000, 1, 0)).bruto == 1500


def test_extra_dos_horas():
    assert procesar(Nomina(0, 1000, 2, 0)).bruto == 3000


def test_impuesto_justo():
    assert procesar(Nomina(1, 100, 0, 10)).impuesto == 10


def test_impuesto_medio_centavo():
    assert procesar(Nomina(1, 105, 0, 10)).impuesto == 11


def test_impuesto_cien():
    assert procesar(Nomina(1, 100, 0, 100)).impuesto == 100


def test_neto_no_negativo_con_tasa_cien():
    assert procesar(Nomina(1, 100, 0, 100)).neto == 0


def test_tarifa_negativa():
    with pytest.raises(ValueError, match="tarifa invalida"):
        procesar(Nomina(1, -1, 0, 10))


def test_extra_negativa():
    with pytest.raises(ValueError, match="horas extra invalidas"):
        procesar(Nomina(1, 100, -1, 10))


def test_tasa_negativa():
    with pytest.raises(ValueError, match="tasa invalida"):
        procesar(Nomina(1, 100, 0, -1))


def test_tasa_mayor_cien():
    with pytest.raises(ValueError, match="tasa invalida"):
        procesar(Nomina(1, 100, 0, 101))


def test_horas_negativas():
    with pytest.raises(ValueError, match="horas invalidas"):
        procesar(Nomina(-1, 100, 0, 10))


def test_combinacion():
    resultado = procesar(Nomina(40, 2000, 10, 20))
    assert resultado.bruto == 110_000
    assert resultado.impuesto == 22_000
    assert resultado.neto == 88_000
