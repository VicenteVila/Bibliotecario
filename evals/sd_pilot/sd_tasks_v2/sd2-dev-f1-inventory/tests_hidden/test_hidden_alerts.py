"""Tests ocultos de las alertas de reposición."""

from inventory.alerts import needs_reorder
from inventory.models import Producto, Reserva


def test_umbral_con_reserva_activa():
    producto = Producto("A", "Caja", 10, 5)
    reservas = [Reserva("A", 5, created_at=0, ttl_seconds=10)]
    assert needs_reorder(producto, reservas, now=0) is True


def test_por_debajo_del_umbral():
    producto = Producto("A", "Caja", 4, 5)
    assert needs_reorder(producto, [], now=0) is True


def test_por_encima_del_umbral():
    producto = Producto("A", "Caja", 6, 5)
    assert needs_reorder(producto, [], now=0) is False


def test_reserva_caducada_no_dispara_alerta():
    producto = Producto("A", "Caja", 6, 5)
    reservas = [Reserva("A", 2, created_at=0, ttl_seconds=1)]
    assert needs_reorder(producto, reservas, now=1) is False
