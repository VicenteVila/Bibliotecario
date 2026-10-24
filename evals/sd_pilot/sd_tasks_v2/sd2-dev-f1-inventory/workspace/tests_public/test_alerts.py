"""Tests públicos de las alertas de reposición."""

from inventory.alerts import needs_reorder
from inventory.models import Producto


def test_umbral_incluyente():
    producto = Producto("A", "Caja", 5, 5)
    assert needs_reorder(producto, [], now=0) is True


def test_por_encima_del_umbral_no_reordena():
    producto = Producto("A", "Caja", 10, 5)
    assert needs_reorder(producto, [], now=0) is False
