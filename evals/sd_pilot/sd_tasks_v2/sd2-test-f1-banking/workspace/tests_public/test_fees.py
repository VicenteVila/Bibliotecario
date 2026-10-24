"""Tests públicos de comisiones."""

from ledger.fees import fee_cents


def test_comision_half_up():
    assert fee_cents(5000, 1) == 1


def test_comision_exacta():
    assert fee_cents(10000, 1) == 1


def test_comision_por_debajo_del_medio():
    assert fee_cents(4999, 1) == 0
