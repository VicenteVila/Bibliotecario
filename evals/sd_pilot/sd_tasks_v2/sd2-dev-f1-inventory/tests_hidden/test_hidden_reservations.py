"""Tests ocultos del ciclo de vida de las reservas."""

from inventory.models import Reserva
from inventory.reservations import is_expired, release_expired


def test_is_expired_limite_exacto():
    reserva = Reserva("A", 1, created_at=100, ttl_seconds=10)
    assert is_expired(reserva, now=110) is True


def test_is_expired_antes_del_limite():
    reserva = Reserva("A", 1, created_at=100, ttl_seconds=10)
    assert is_expired(reserva, now=109) is False


def test_is_expired_despues_del_limite():
    reserva = Reserva("A", 1, created_at=100, ttl_seconds=10)
    assert is_expired(reserva, now=111) is True


def test_release_marca_solo_las_caducadas():
    caducada = Reserva("A", 1, created_at=0, ttl_seconds=5)
    viva = Reserva("A", 1, created_at=4, ttl_seconds=5)
    resultado = release_expired([caducada, viva], now=5)
    assert resultado[0].status == "expired"
    assert resultado[1].status == "active"
    assert caducada.status == "active"


def test_release_es_idempotente():
    caducada = Reserva("A", 1, created_at=0, ttl_seconds=5)
    una = release_expired([caducada], now=5)
    dos = release_expired(una, now=6)
    assert dos[0].status == "expired"


def test_release_no_toca_canceladas():
    cancelada = Reserva(
        "A", 1, created_at=0, ttl_seconds=5, status="cancelled"
    )
    resultado = release_expired([cancelada], now=10)
    assert resultado[0].status == "cancelled"
