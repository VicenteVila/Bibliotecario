"""Tests ocultos de logística."""

import pytest
from logistica.models import Envio
from logistica.service import procesar


def test_solo_peso():
    assert procesar(Envio(1, 0, 0)).base == 520


def test_solo_volumen():
    assert procesar(Envio(0, 1, 0)).base == 502


def test_solo_distancia():
    assert procesar(Envio(0, 0, 1)).base == 510


def test_express_base_impar():
    resultado = procesar(Envio(0, 1, 0, express=True))
    assert resultado.base == 502
    assert resultado.recargos == 251


def test_express_total_exacto():
    resultado = procesar(Envio(15, 0, 0, express=True))
    assert resultado.total == 1200


def test_minimo_con_express():
    resultado = procesar(Envio(0, 0, 0, express=True))
    assert resultado.base == 500
    assert resultado.recargos == 250
    assert resultado.total == 1000


def test_justo_en_el_minimo():
    resultado = procesar(Envio(0, 0, 50))
    assert resultado.base == 1000
    assert resultado.total == 1000


def test_un_centavo_bajo_el_minimo():
    resultado = procesar(Envio(0, 0, 0))
    assert resultado.total == 1000


def test_express_por_encima_del_minimo():
    resultado = procesar(Envio(10, 0, 0, express=True))
    assert resultado.base == 700
    assert resultado.recargos == 350
    assert resultado.total == 1050


def test_todo_grande():
    resultado = procesar(Envio(100, 100, 100))
    assert resultado.base == 3700
    assert resultado.total == 3700


def test_negativo_tiene_prioridad():
    with pytest.raises(ValueError, match="peso invalido"):
        procesar(Envio(-1, -1, -1))


def test_express_no_cambia_base():
    normal = procesar(Envio(3, 4, 5))
    express = procesar(Envio(3, 4, 5, express=True))
    assert normal.base == express.base
