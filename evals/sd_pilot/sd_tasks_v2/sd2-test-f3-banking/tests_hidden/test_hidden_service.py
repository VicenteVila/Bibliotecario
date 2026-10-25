"""Tests ocultos de la fachada del libro."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.service import Ledger


def test_constructor_copia_la_lista():
    asientos = [Asiento("p", "A", 50)]
    ledger = Ledger(Cuenta("A", 0, 500), asientos)
    asientos.append(Asiento("q", "A", 999))
    assert ledger.saldo() == 50


def test_saldo_ignora_pendientes_y_revertidos():
    ledger = Ledger(
        Cuenta("A", 100, 500),
        [
            Asiento("p", "A", 50),
            Asiento("q", "A", 70, status="pending"),
            Asiento("r", "A", -30, status="reversed"),
        ],
    )
    assert ledger.saldo() == 150


def test_registrar_pendiente_no_cambia_saldo():
    ledger = Ledger(Cuenta("A", 100, 500), [])
    ledger.registrar(Asiento("p", "A", 50, status="pending"))
    assert ledger.saldo() == 100
    assert len(ledger.asientos_actuales()) == 1


def test_registrar_limite_exacto():
    ledger = Ledger(Cuenta("A", 0, 500), [])
    ledger.registrar(Asiento("p", "A", -500))
    assert ledger.saldo() == -500


def test_registrar_excedido_no_muta():
    ledger = Ledger(Cuenta("A", 0, 500), [])
    with pytest.raises(ValueError, match="limite de descubierto excedido"):
        ledger.registrar(Asiento("p", "A", -501))
    assert ledger.saldo() == 0
    assert ledger.asientos_actuales() == ()


def test_registrar_duplicado_pendiente():
    ledger = Ledger(
        Cuenta("A", 0, 500),
        [Asiento("p", "A", 10, status="pending")],
    )
    with pytest.raises(ValueError, match="asiento duplicado: p"):
        ledger.registrar(Asiento("p", "A", 20))


def test_registrar_varios():
    ledger = Ledger(Cuenta("A", 0, 500), [])
    ledger.registrar(Asiento("p", "A", 50))
    ledger.registrar(Asiento("q", "A", -20))
    assert ledger.saldo() == 30


def test_informe_igual_a_saldo_con_posted():
    ledger = Ledger(
        Cuenta("A", 10, 500),
        [Asiento("p", "A", 50), Asiento("q", "A", -20)],
    )
    assert ledger.informe() == ledger.saldo() == 40


def test_asientos_actuales_tras_registrar():
    ledger = Ledger(Cuenta("A", 0, 500), [])
    ledger.registrar(Asiento("p", "A", 50))
    assert ledger.asientos_actuales() == (Asiento("p", "A", 50),)


def test_registrar_no_muta_la_entrada():
    ledger = Ledger(Cuenta("A", 0, 500), [])
    asiento = Asiento("p", "A", 50)
    ledger.registrar(asiento)
    assert asiento.status == "posted"
