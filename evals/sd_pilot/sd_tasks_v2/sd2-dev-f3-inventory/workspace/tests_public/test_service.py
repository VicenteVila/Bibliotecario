"""Tests públicos de la fachada de inventario."""

import pytest
from inventory.models import Producto, Reserva
from inventory.service import Inventario


def _inventario() -> Inventario:
    productos = {
        "A": Producto("A", "Caja", 10, 5),
        "B": Producto("B", "Sobre", 3, 2),
    }
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=10)]
    return Inventario(productos, reservas)


def test_disponible():
    assert _inventario().disponible("A", now=0) == 6


def test_alerta_umbral():
    inventario = Inventario({"A": Producto("A", "Caja", 5, 5)}, [])
    assert inventario.alerta("A", now=0) is True


def test_liberar_caducadas():
    inventario = _inventario()
    assert inventario.liberar(now=10) == 1
    assert inventario.disponible("A", now=10) == 10


def test_liberar_sin_caducadas():
    assert _inventario().liberar(now=9) == 0


def test_sku_desconocido():
    with pytest.raises(KeyError):
        _inventario().disponible("Z", now=0)
