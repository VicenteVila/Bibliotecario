"""Tests ocultos del stock disponible."""

from inventory.models import Producto, Reserva
from inventory.stock import available_stock


def test_caducidad_exacta_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=10, ttl_seconds=3)]
    assert available_stock(producto, reservas, now=13) == 10


def test_antes_de_caducar_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=10, ttl_seconds=3)]
    assert available_stock(producto, reservas, now=12) == 6


def test_cancelada_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=3, status="cancelled")]
    assert available_stock(producto, reservas, now=0) == 10


def test_ya_caducada_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=3, status="expired")]
    assert available_stock(producto, reservas, now=0) == 10


def test_otro_sku_no_resta():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("B", 4, created_at=0, ttl_seconds=3)]
    assert available_stock(producto, reservas, now=0) == 10


def test_varias_reservas_y_caducada():
    producto = Producto("A", "Caja", 20, 5)
    reservas = [
        Reserva("A", 2, created_at=0, ttl_seconds=10),
        Reserva("A", 3, created_at=1, ttl_seconds=10),
        Reserva("A", 4, created_at=0, ttl_seconds=1),
    ]
    assert available_stock(producto, reservas, now=2) == 15


def test_disponible_puede_ser_cero():
    producto = Producto("A", "Caja", 5, 5)
    reservas = [Reserva("A", 5, created_at=0, ttl_seconds=10)]
    assert available_stock(producto, reservas, now=0) == 0
