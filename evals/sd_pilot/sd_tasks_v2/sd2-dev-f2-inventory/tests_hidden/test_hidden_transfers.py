"""Tests ocultos de transferencias."""

import pytest
from inventory.models import Producto, Reserva
from inventory.transfers import plan_transfer


def _productos(sku_o: str = "A", sku_d: str = "A", stock: int = 10):
    return (
        Producto(sku_o, "Origen", stock, 2),
        Producto(sku_d, "Destino", 1, 2),
    )


def test_cero_invalido():
    origen, destino = _productos()
    with pytest.raises(ValueError, match="cantidad invalida: 0"):
        plan_transfer(origen, destino, [], 0, now=0)


def test_negativo_invalido():
    origen, destino = _productos()
    with pytest.raises(ValueError, match="cantidad invalida: -3"):
        plan_transfer(origen, destino, [], -3, now=0)


def test_sku_distinto():
    origen, destino = _productos(sku_o="A", sku_d="B")
    with pytest.raises(ValueError, match="sku distinto: A != B"):
        plan_transfer(origen, destino, [], 1, now=0)


def test_exacto_con_reserva_activa():
    origen, destino = _productos(stock=10)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=10)]
    assert plan_transfer(origen, destino, reservas, 6, now=0).cantidad == 6


def test_uno_por_encima_de_lo_disponible():
    origen, destino = _productos(stock=10)
    reservas = [Reserva("A", 4, created_at=0, ttl_seconds=10)]
    with pytest.raises(ValueError, match="stock insuficiente: 7"):
        plan_transfer(origen, destino, reservas, 7, now=0)


def test_reserva_caducada_no_bloquea():
    origen, destino = _productos(stock=5)
    reservas = [Reserva("A", 5, created_at=0, ttl_seconds=1)]
    assert plan_transfer(origen, destino, reservas, 5, now=1).cantidad == 5


def test_reserva_cancelada_no_bloquea():
    origen, destino = _productos(stock=5)
    reservas = [
        Reserva("A", 5, created_at=0, ttl_seconds=10, status="cancelled")
    ]
    assert plan_transfer(origen, destino, reservas, 5, now=0).cantidad == 5


def test_reserva_de_otro_sku_no_bloquea():
    origen, destino = _productos(stock=5)
    reservas = [Reserva("B", 5, created_at=0, ttl_seconds=10)]
    assert plan_transfer(origen, destino, reservas, 5, now=0).cantidad == 5


def test_varias_reservas_activas():
    origen, destino = _productos(stock=10)
    reservas = [
        Reserva("A", 2, created_at=0, ttl_seconds=10),
        Reserva("A", 3, created_at=0, ttl_seconds=10),
    ]
    with pytest.raises(ValueError, match="stock insuficiente: 6"):
        plan_transfer(origen, destino, reservas, 6, now=0)


def test_no_muta_la_lista_de_reservas():
    origen, destino = _productos(stock=5)
    reservas = [Reserva("A", 1, created_at=0, ttl_seconds=10)]
    plan_transfer(origen, destino, reservas, 1, now=0)
    assert reservas == [Reserva("A", 1, created_at=0, ttl_seconds=10)]


def test_devuelve_los_campos_de_la_transferencia():
    origen, destino = _productos(stock=5)
    transferencia = plan_transfer(origen, destino, [], 2, now=0)
    assert transferencia.sku == "A"
    assert transferencia.cantidad == 2
    assert transferencia.origen == "A"
    assert transferencia.destino == "A"
