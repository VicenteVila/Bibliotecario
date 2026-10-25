"""Tests públicos de reservas."""

from reservas.models import Reserva
from reservas.service import procesar


def test_disponible_con_activa():
    reservas = [Reserva("a", 2, 0, 10)]
    assert procesar(10, reservas, 3).disponible == 8


def test_disponible_ignora_caducada():
    reservas = [Reserva("a", 2, 0, 10)]
    assert procesar(10, reservas, 10).disponible == 10


def test_caducadas_limite_exacto():
    reservas = [Reserva("a", 2, 0, 10)]
    assert procesar(10, reservas, 10).caducadas == 1


def test_alerta_umbral():
    reservas = [Reserva("a", 9, 0, 10)]
    assert procesar(10, reservas, 1).alerta is True


def test_alerta_por_encima():
    reservas = [Reserva("a", 8, 0, 10)]
    assert procesar(10, reservas, 1).alerta is False


def test_sin_caducadas():
    reservas = [Reserva("a", 1, 0, 10)]
    assert procesar(10, reservas, 1).caducadas == 0
