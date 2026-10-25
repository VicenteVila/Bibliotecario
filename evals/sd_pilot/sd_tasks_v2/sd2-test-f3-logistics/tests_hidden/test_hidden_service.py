"""Tests ocultos de la fachada logística."""

import pytest
from logistica.models import Envio
from logistica.service import Cotizador


def test_solo_peso():
    assert Cotizador(Envio(1, 0, 0)).base() == 520


def test_express_impar():
    cotizador = Cotizador(Envio(0, 1, 0, express=True))
    assert cotizador.recargos() == 251


def test_minimo():
    assert Cotizador(Envio(0, 0, 0)).total() == 1000


def test_minimo_con_express():
    cotizador = Cotizador(Envio(0, 0, 0, express=True))
    assert cotizador.total() == 1000


def test_justo_minimo():
    assert Cotizador(Envio(0, 0, 50)).total() == 1000


def test_volumen_negativo():
    with pytest.raises(ValueError, match="volumen invalido"):
        Cotizador(Envio(0, -1, 0)).base()


def test_distancia_negativa():
    with pytest.raises(ValueError, match="distancia invalida"):
        Cotizador(Envio(0, 0, -1)).base()


def test_todo_grande():
    assert Cotizador(Envio(100, 100, 100)).total() == 3700


def test_express_no_cambia_base():
    normal = Cotizador(Envio(3, 4, 5))
    express = Cotizador(Envio(3, 4, 5, express=True))
    assert normal.base() == express.base()


def test_procesar_coherente():
    cotizador = Cotizador(Envio(10, 0, 0, express=True))
    resultado = cotizador.procesar()
    assert resultado.base == cotizador.base()
    assert resultado.recargos == cotizador.recargos()
    assert resultado.total == cotizador.total()
