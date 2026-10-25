"""Tests públicos de la fachada de nómina."""

import pytest
from nomina.models import Nomina
from nomina.service import CalculoNomina


def _calculo() -> CalculoNomina:
    return CalculoNomina(Nomina(10, 1000, 5, 15))


def test_bruto():
    assert _calculo().bruto() == 17_500


def test_impuesto():
    assert _calculo().impuesto() == 2_625


def test_neto():
    assert _calculo().neto() == 14_875


def test_procesar():
    resultado = _calculo().procesar()
    assert resultado.bruto == 17_500
    assert resultado.neto == 14_875


def test_horas_negativas():
    with pytest.raises(ValueError, match="horas invalidas"):
        CalculoNomina(Nomina(-1, 100, 0, 10)).bruto()
