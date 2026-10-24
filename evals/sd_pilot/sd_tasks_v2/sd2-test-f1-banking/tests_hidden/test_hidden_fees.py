"""Tests ocultos de comisiones."""

from ledger.fees import fee_cents


def test_redondeo_quarter_up():
    assert fee_cents(2500, 1) == 0


def test_redondeo_half_up():
    assert fee_cents(5000, 1) == 1


def test_redondeo_three_quarters_up():
    assert fee_cents(7500, 1) == 1


def test_redondeo_uno_y_medio():
    assert fee_cents(15000, 1) == 2


def test_comision_cero():
    assert fee_cents(0, 500) == 0


def test_comision_exacta_sin_redondeo():
    assert fee_cents(10000, 3) == 3
