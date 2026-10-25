"""Tests ocultos de la fachada de reservas."""

import pytest
from reservas.models import Reserva
from reservas.service import Reservas


def test_disponible_cero():
    assert Reservas(0, [], 0).disponible() == 0


def test_cantidad_invalida():
    with pytest.raises(ValueError, match="cantidad invalida: a"):
        Reservas(10, [Reserva("a", 0, 0, 10)], 0).disponible()


def test_caducidad_exacta():
    reservas = Reservas(10, [Reserva("a", 2, 0, 10)], 10)
    assert reservas.disponible() == 10
    assert reservas.caducadas() == 1


def test_caducidad_una_unidad_antes():
    reservas = Reservas(10, [Reserva("a", 2, 0, 10)], 9)
    assert reservas.disponible() == 8


def test_cancelada_no_resta():
    reservas = Reservas(
        10, [Reserva("a", 2, 0, 10, status="cancelled")], 100
    )
    assert reservas.disponible() == 10
    assert reservas.caducadas() == 0


def test_mezcla_caducada_y_activa():
    reservas = Reservas(
        10,
        [Reserva("a", 2, 0, 10), Reserva("b", 3, 0, 100)],
        10,
    )
    assert reservas.disponible() == 7
    assert reservas.caducadas() == 1


def test_alerta_uno():
    assert Reservas(10, [Reserva("a", 9, 0, 10)], 1).alerta() is True


def test_alerta_cero():
    assert Reservas(10, [Reserva("a", 10, 0, 10)], 1).alerta() is True


def test_sin_alerta_dos():
    assert Reservas(10, [Reserva("a", 8, 0, 10)], 1).alerta() is False


def test_procesar_coherente():
    resultado = Reservas(
        10, [Reserva("a", 9, 0, 10)], 1
    ).procesar()
    assert resultado.disponible == 1
    assert resultado.caducadas == 0
    assert resultado.alerta is True
