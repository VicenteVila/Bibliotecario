"""Tests públicos de logística."""

import pytest
from logistica.models import Envio
from logistica.service import procesar


def test_envio_normal():
    resultado = procesar(Envio(10, 20, 100))
    assert resultado.base == 1740
    assert resultado.recargos == 0
    assert resultado.total == 1740


def test_express_mitad():
    resultado = procesar(Envio(15, 0, 0, express=True))
    assert resultado.base == 800
    assert resultado.recargos == 400
    assert resultado.total == 1200


def test_minimo_de_tarifa():
    resultado = procesar(Envio(0, 0, 0))
    assert resultado.base == 500
    assert resultado.total == 1000


def test_peso_negativo():
    with pytest.raises(ValueError, match="peso invalido"):
        procesar(Envio(-1, 0, 0))


def test_volumen_negativo():
    with pytest.raises(ValueError, match="volumen invalido"):
        procesar(Envio(0, -1, 0))


def test_distancia_negativa():
    with pytest.raises(ValueError, match="distancia invalida"):
        procesar(Envio(0, 0, -1))
