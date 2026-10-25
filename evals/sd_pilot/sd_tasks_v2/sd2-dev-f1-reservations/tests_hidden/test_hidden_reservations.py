"""Tests ocultos de reservas."""

import pytest
from reservas.models import Reserva
from reservas.service import procesar


def test_capacidad_cero():
    assert procesar(0, [], 0).disponible == 0


def test_capacidad_negativa():
    with pytest.raises(ValueError, match="capacidad invalida"):
        procesar(-1, [], 0)


def test_cantidad_cero():
    with pytest.raises(ValueError, match="cantidad invalida: a"):
        procesar(10, [Reserva("a", 0, 0, 10)], 0)


def test_cantidad_negativa():
    with pytest.raises(ValueError, match="cantidad invalida: a"):
        procesar(10, [Reserva("a", -1, 0, 10)], 0)


def test_ttl_cero_caduca_de_inmediato():
    reservas = [Reserva("a", 2, 0, 0)]
    resultado = procesar(10, reservas, 0)
    assert resultado.disponible == 10
    assert resultado.caducadas == 1


def test_una_unidad_antes_caduca():
    reservas = [Reserva("a", 2, 0, 10)]
    assert procesar(10, reservas, 9).disponible == 8


def test_caducada_no_resta_pero_activa_si():
    reservas = [
        Reserva("a", 2, 0, 10),
        Reserva("b", 3, 0, 100),
    ]
    resultado = procesar(10, reservas, 10)
    assert resultado.disponible == 7
    assert resultado.caducadas == 1


def test_cancelada_no_resta_ni_caduca():
    reservas = [Reserva("a", 2, 0, 10, status="cancelled")]
    resultado = procesar(10, reservas, 100)
    assert resultado.disponible == 10
    assert resultado.caducadas == 0


def test_alerta_cuando_disponible_uno():
    reservas = [Reserva("a", 9, 0, 10)]
    assert procesar(10, reservas, 1).alerta is True


def test_alerta_cuando_disponible_cero():
    reservas = [Reserva("a", 10, 0, 10)]
    assert procesar(10, reservas, 1).alerta is True


def test_sin_alerta_cuando_disponible_dos():
    reservas = [Reserva("a", 8, 0, 10)]
    assert procesar(10, reservas, 1).alerta is False


def test_sobreventa_da_negativo():
    reservas = [Reserva("a", 12, 0, 10)]
    assert procesar(10, reservas, 1).disponible == -2
