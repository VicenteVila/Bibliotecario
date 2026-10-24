"""Tests públicos: redondeo monetario del checkout (guía, no es exhaustivo)."""

from decimal import Decimal

import pytest
from checkout.redondeo import a_decimal, redondear


def test_redondear_empate_half_up():
    assert redondear(Decimal("1.005"), 2) == Decimal("1.01")


def test_redondear_en_cero_decimales():
    assert redondear(Decimal("3.5"), 0) == Decimal(4)


def test_a_decimal_no_admite_float():
    with pytest.raises(TypeError, match="float prohibido para dinero"):
        a_decimal(19.99)
