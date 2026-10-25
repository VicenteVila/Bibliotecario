"""Tests públicos de reversión."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.reversal import apply_reversal, reverse_entry


def test_revierte_posted():
    original = Asiento("x", "A", 100)
    reverso = reverse_entry(original, "error")
    assert reverso.asiento_id == "rev-x"
    assert reverso.cuenta_id == "A"
    assert reverso.amount_cents == -100
    assert reverso.status == "posted"


def test_no_revierte_pendiente():
    with pytest.raises(ValueError, match="solo se revierten asientos posted"):
        reverse_entry(Asiento("x", "A", 100, status="pending"), "error")


def test_motivo_obligatorio():
    with pytest.raises(ValueError, match="motivo requerido"):
        reverse_entry(Asiento("x", "A", 100), "")


def test_apply_anade_el_reverso():
    cuenta = Cuenta("A", 0, 1000)
    original = Asiento("x", "A", 100)
    resultado = apply_reversal(cuenta, [original], "x", "error")
    assert resultado[-1].asiento_id == "rev-x"
    assert resultado[-1].amount_cents == -100


def test_no_permite_doble_reversion():
    cuenta = Cuenta("A", 0, 1000)
    original = Asiento("x", "A", 100)
    una = apply_reversal(cuenta, [original], "x", "error")
    with pytest.raises(ValueError, match="asiento ya revertido"):
        apply_reversal(cuenta, una, "x", "otra")


def test_asiento_inexistente():
    cuenta = Cuenta("A", 0, 1000)
    with pytest.raises(ValueError, match="asiento no encontrado: z"):
        apply_reversal(cuenta, [], "z", "error")
