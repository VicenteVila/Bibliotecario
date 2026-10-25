"""Tests ocultos de reversión."""

import pytest
from ledger.models import Asiento, Cuenta
from ledger.reversal import apply_reversal, reverse_entry


def test_no_revierte_ya_revertido():
    with pytest.raises(ValueError, match="solo se revierten asientos posted"):
        reverse_entry(Asiento("x", "A", 100, status="reversed"), "error")


def test_no_revierte_pendiente():
    with pytest.raises(ValueError, match="solo se revierten asientos posted"):
        reverse_entry(Asiento("x", "A", 100, status="pending"), "error")


def test_motivo_vacio():
    with pytest.raises(ValueError, match="motivo requerido"):
        reverse_entry(Asiento("x", "A", 100), "")


def test_revierte_importe_negativo():
    reverso = reverse_entry(Asiento("x", "A", -250), "ajuste")
    assert reverso.amount_cents == 250


def test_apply_preserva_el_original():
    cuenta = Cuenta("A", 0, 1000)
    original = Asiento("x", "A", 100)
    resultado = apply_reversal(cuenta, [original], "x", "error")
    assert resultado[0] is original
    assert len(resultado) == 2


def test_apply_no_muta_la_secuencia():
    cuenta = Cuenta("A", 0, 1000)
    asientos = [Asiento("x", "A", 100)]
    apply_reversal(cuenta, asientos, "x", "error")
    assert len(asientos) == 1


def test_apply_doble_reversion():
    cuenta = Cuenta("A", 0, 1000)
    original = Asiento("x", "A", 100)
    una = apply_reversal(cuenta, [original], "x", "error")
    with pytest.raises(ValueError, match="asiento ya revertido"):
        apply_reversal(cuenta, una, "x", "otra")


def test_apply_pendiente():
    cuenta = Cuenta("A", 0, 1000)
    with pytest.raises(ValueError, match="solo se revierten asientos posted"):
        apply_reversal(cuenta, [Asiento("x", "A", 100, status="pending")], "x", "error")


def test_apply_motivo_vacio():
    cuenta = Cuenta("A", 0, 1000)
    with pytest.raises(ValueError, match="motivo requerido"):
        apply_reversal(cuenta, [Asiento("x", "A", 100)], "x", "")


def test_apply_inexistente():
    cuenta = Cuenta("A", 0, 1000)
    with pytest.raises(ValueError, match="asiento no encontrado: z"):
        apply_reversal(cuenta, [Asiento("x", "A", 100)], "z", "error")
