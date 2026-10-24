"""Tests públicos del registro de asientos."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.posting import balance_cents, post


def test_descubierto_en_el_limite_exacto():
    cuenta = Cuenta("A", 0, 1000)
    nuevo = Asiento("x", "A", -1000)
    assert post(cuenta, [], nuevo) == (nuevo,)


def test_descubierto_por_encima_del_limite():
    cuenta = Cuenta("A", 0, 1000)
    with pytest.raises(ValueError, match="limite de descubierto excedido"):
        post(cuenta, [], Asiento("x", "A", -1001))


def test_duplicado_en_cualquier_estado():
    cuenta = Cuenta("A", 0, 1000)
    pendiente = Asiento("x", "A", 10, status="pending")
    with pytest.raises(ValueError, match="asiento duplicado: x"):
        post(cuenta, [pendiente], Asiento("x", "A", 20))


def test_saldo_ignora_pendientes():
    cuenta = Cuenta("A", 100, 1000)
    asientos = [
        Asiento("p", "A", 50, status="posted"),
        Asiento("q", "A", 70, status="pending"),
    ]
    assert balance_cents(cuenta, asientos) == 150
