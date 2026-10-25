"""Tests ocultos de la fachada de inventario."""

import pytest
from inventory.models import Producto, Reserva
from inventory.service import Inventario


def test_disponible_con_varios_skus():
    inventario = Inventario(
        {
            "A": Producto("A", "Caja", 10, 5),
            "B": Producto("B", "Sobre", 4, 2),
        },
        [Reserva("A", 3, created_at=0, ttl_seconds=10)],
    )
    assert inventario.disponible("A", now=0) == 7
    assert inventario.disponible("B", now=0) == 4


def test_disponible_ignora_caducada():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 10, 5)},
        [Reserva("A", 4, created_at=0, ttl_seconds=2)],
    )
    assert inventario.disponible("A", now=2) == 10


def test_alerta_umbral_exacto():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 5, 5)},
        [],
    )
    assert inventario.alerta("A", now=0) is True


def test_alerta_por_encima():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 6, 5)},
        [],
    )
    assert inventario.alerta("A", now=0) is False


def test_liberar_cuenta_y_actualiza():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 10, 5)},
        [
            Reserva("A", 2, created_at=0, ttl_seconds=1),
            Reserva("A", 3, created_at=0, ttl_seconds=10),
        ],
    )
    assert inventario.liberar(now=1) == 1
    estados = [r.status for r in inventario.reservas_actuales()]
    assert estados == ["expired", "active"]


def test_liberar_es_idempotente():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 10, 5)},
        [Reserva("A", 2, created_at=0, ttl_seconds=1)],
    )
    assert inventario.liberar(now=1) == 1
    assert inventario.liberar(now=2) == 0


def test_liberar_no_toca_otro_sku():
    inventario = Inventario(
        {
            "A": Producto("A", "Caja", 10, 5),
            "B": Producto("B", "Sobre", 10, 5),
        },
        [
            Reserva("A", 2, created_at=0, ttl_seconds=1),
            Reserva("B", 3, created_at=0, ttl_seconds=1),
        ],
    )
    assert inventario.liberar(now=1) == 2
    assert inventario.disponible("A", now=1) == 10
    assert inventario.disponible("B", now=1) == 10


def test_reservas_actuales_es_tupla():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 10, 5)},
        [Reserva("A", 1, created_at=0, ttl_seconds=5)],
    )
    assert isinstance(inventario.reservas_actuales(), tuple)


def test_constructor_copia_la_lista():
    reservas = [Reserva("A", 1, created_at=0, ttl_seconds=5)]
    inventario = Inventario({"A": Producto("A", "Caja", 10, 5)}, reservas)
    reservas.append(Reserva("A", 9, created_at=0, ttl_seconds=5))
    assert inventario.disponible("A", now=0) == 9


def test_alerta_sku_desconocido():
    inventario = Inventario({"A": Producto("A", "Caja", 10, 5)}, [])
    with pytest.raises(KeyError):
        inventario.alerta("Z", now=0)


def test_liberar_limite_exacto():
    inventario = Inventario(
        {"A": Producto("A", "Caja", 10, 5)},
        [Reserva("A", 1, created_at=5, ttl_seconds=3)],
    )
    assert inventario.liberar(now=8) == 1
