"""Tests ocultos del registro de asientos."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.posting import balance_cents, post


def test_limite_exacto_permitido():
    cuenta = Cuenta("A", 0, 500)
    nuevo = Asiento("x", "A", -500)
    assert post(cuenta, [], nuevo) == (nuevo,)


def test_justo_por_debajo_del_limite_permitido():
    cuenta = Cuenta("A", 0, 500)
    nuevo = Asiento("x", "A", -499)
    assert post(cuenta, [], nuevo) == (nuevo,)


def test_limite_excedido_por_un_centimo():
    cuenta = Cuenta("A", 0, 500)
    with pytest.raises(ValueError, match="limite de descubierto excedido"):
        post(cuenta, [], Asiento("x", "A", -501))


def test_duplicado_pendiente():
    cuenta = Cuenta("A", 0, 500)
    pendiente = Asiento("x", "A", 10, status="pending")
    with pytest.raises(ValueError, match="asiento duplicado: x"):
        post(cuenta, [pendiente], Asiento("x", "A", 20))


def test_duplicado_revertido():
    cuenta = Cuenta("A", 0, 500)
    revertido = Asiento("x", "A", 10, status="reversed")
    with pytest.raises(ValueError, match="asiento duplicado: x"):
        post(cuenta, [revertido], Asiento("x", "A", 20))


def test_saldo_ignora_pendientes_y_revertidos():
    cuenta = Cuenta("A", 100, 500)
    asientos = [
        Asiento("p", "A", 50),
        Asiento("q", "A", 70, status="pending"),
        Asiento("r", "A", -30, status="reversed"),
    ]
    assert balance_cents(cuenta, asientos) == 150


def test_post_no_muta_la_lista_original():
    cuenta = Cuenta("A", 0, 500)
    asientos: list[Asiento] = []
    post(cuenta, asientos, Asiento("x", "A", 10))
    assert asientos == []
