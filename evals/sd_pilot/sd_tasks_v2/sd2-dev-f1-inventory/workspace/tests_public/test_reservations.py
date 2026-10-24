"""Tests públicos del ciclo de vida de las reservas."""

from inventory.models import Reserva
from inventory.reservations import is_expired, release_expired


def test_ttl_exacto_caduca():
    reserva = Reserva("A", 1, created_at=0, ttl_seconds=5)
    assert is_expired(reserva, now=5) is True


def test_antes_del_ttl_sigue_activa():
    reserva = Reserva("A", 1, created_at=0, ttl_seconds=5)
    liberadas = release_expired([reserva], now=4)
    assert liberadas[0].status == "active"
