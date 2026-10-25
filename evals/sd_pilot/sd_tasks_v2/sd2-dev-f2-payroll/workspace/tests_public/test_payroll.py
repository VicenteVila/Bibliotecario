"""Tests públicos de nómina."""

from nomina.models import Nomina
from nomina.service import procesar


def test_sin_extra():
    resultado = procesar(Nomina(100, 1000, 0, 15))
    assert resultado.bruto == 100_000
    assert resultado.impuesto == 15_000
    assert resultado.neto == 85_000


def test_extra_al_150_por_ciento():
    resultado = procesar(Nomina(10, 1000, 5, 15))
    assert resultado.bruto == 17_500
    assert resultado.impuesto == 2_625
    assert resultado.neto == 14_875


def test_impuesto_redondeo_hacia_arriba():
    assert procesar(Nomina(1, 1010, 0, 15)).impuesto == 152


def test_tasa_cero():
    resultado = procesar(Nomina(10, 100, 0, 0))
    assert resultado.impuesto == 0
    assert resultado.neto == 1000


def test_todo_cero():
    resultado = procesar(Nomina(0, 0, 0, 0))
    assert resultado.bruto == 0
    assert resultado.neto == 0


def test_horas_negativas():
    try:
        procesar(Nomina(-1, 100, 0, 10))
    except ValueError:
        return
    raise AssertionError("se esperaba ValueError")
