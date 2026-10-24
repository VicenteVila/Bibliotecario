"""Tests públicos del stock disponible."""

from inventory.models import Producto, Reserva
from inventory.stock import available_stock


def test_reserva_activa_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=5)]
    assert available_stock(producto, reservas, now=0) == 6


def test_reserva_caducada_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=5)]
    assert available_stock(producto, reservas, now=5) == 10


def test_otro_sku_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("B", 4, created_at=0, ttl_seconds=5)]
    assert available_stock(producto, reservas, now=0) == 10
