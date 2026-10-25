"""Tests públicos de la fachada del libro."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.service import Ledger


def _ledger() -> Ledger:
    return Ledger(
        Cuenta("A", 100, 500),
        [Asiento("p", "A", 50), Asiento("q", "A", 30, status="pending")],
    )


def test_saldo():
    assert _ledger().saldo() == 150


def test_registrar():
    ledger = _ledger()
    ledger.registrar(Asiento("r", "A", -20))
    assert ledger.saldo() == 130


def test_registrar_duplicado():
    ledger = _ledger()
    with pytest.raises(ValueError, match="asiento duplicado: p"):
        ledger.registrar(Asiento("p", "A", 10))


def test_registrar_descubierto():
    ledger = Ledger(Cuenta("A", 0, 100), [])
    with pytest.raises(ValueError, match="limite de descubierto excedido"):
        ledger.registrar(Asiento("r", "A", -101))


def test_informe_ignora_pendientes():
    assert _ledger().informe() == 150


def test_asientos_actuales_es_tupla():
    assert isinstance(_ledger().asientos_actuales(), tuple)
