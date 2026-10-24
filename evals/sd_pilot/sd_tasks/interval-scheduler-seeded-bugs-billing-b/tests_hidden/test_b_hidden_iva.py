"""Tests ocultos: IVA con redondeo half-up exacto."""

from facturacion.impuestos import TASA_IVA_DEFECTO, iva_cents


def test_iva_terminacion_5_half_up():
    assert iva_cents(1250) == 263  # 262.5 -> 263


def test_iva_valores_varios():
    assert iva_cents(1000) == 210
    assert iva_cents(1201) == 252  # 252.21
    assert iva_cents(119) == 25    # 24.99 -> 25
    assert iva_cents(0) == 0


def test_iva_tasa_cero():
    assert iva_cents(1000, tasa_pct=0) == 0


def test_tasa_por_defecto_documentada():
    assert TASA_IVA_DEFECTO == 21
    assert iva_cents(100) == iva_cents(100, TASA_IVA_DEFECTO)
