"""Tests públicos de transferencias."""

import pytest
from inventory.models import Producto, Reserva
from inventory.transfers import plan_transfer


def test_transferencia_simple():
    origen = Producto("A", "Origen", 10, 2)
    destino = Producto("A", "Destino", 1, 2)
    transferencia = plan_transfer(origen, destino, [], 3, now=0)
    assert transferencia.sku == "A"
    assert transferencia.cantidad == 3
    assert transferencia.origen == "A"
    assert transferencia.destino == "A"


def test_reserva_activa_reduce_lo_transferible():
    origen = Producto("A", "Origen", 5, 2)
    destino = Producto("A", "Destino", 1, 2)
    reservas = [Reserva("A", 2, created_at=0, ttl_seconds=10)]
    with pytest.raises(ValueError, match="stock insuficiente: 4"):
        plan_transfer(origen, destino, reservas, 4, now=0)


def test_cantidad_cero_invalida():
    origen = Producto("A", "Origen", 5, 2)
    destino = Producto("A", "Destino", 1, 2)
    with pytest.raises(ValueError, match="cantidad invalida: 0"):
        plan_transfer(origen, destino, [], 0, now=0)


def test_sku_distinto_invalido():
    origen = Producto("A", "Origen", 5, 2)
    destino = Producto("B", "Destino", 1, 2)
    with pytest.raises(ValueError, match="sku distinto: A != B"):
        plan_transfer(origen, destino, [], 1, now=0)


def test_cantidad_exactamente_disponible():
    origen = Producto("A", "Origen", 5, 2)
    destino = Producto("A", "Destino", 1, 2)
    assert plan_transfer(origen, destino, [], 5, now=0).cantidad == 5


def test_cantidad_negativa_invalida():
    origen = Producto("A", "Origen", 5, 2)
    destino = Producto("A", "Destino", 1, 2)
    with pytest.raises(ValueError, match="cantidad invalida: -1"):
        plan_transfer(origen, destino, [], -1, now=0)
