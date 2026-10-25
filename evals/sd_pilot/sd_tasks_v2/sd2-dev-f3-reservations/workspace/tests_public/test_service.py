"""Tests públicos de la fachada de reservas."""

import pytest
from reservas.models import Reserva
from reservas.service import Reservas


def _reservas() -> Reservas:
    return Reservas(10, [Reserva("a", 2, 0, 10)], 3)


def test_disponible():
    assert _reservas().disponible() == 8


def test_caducadas():
    assert _reservas().caducadas() == 0


def test_alerta():
    assert Reservas(10, [Reserva("a", 9, 0, 10)], 1).alerta() is True


def test_procesar():
    resultado = _reservas().procesar()
    assert resultado.disponible == 8
    assert resultado.alerta is False


def test_capacidad_negativa():
    with pytest.raises(ValueError, match="capacidad invalida"):
        Reservas(-1, [], 0).disponible()
