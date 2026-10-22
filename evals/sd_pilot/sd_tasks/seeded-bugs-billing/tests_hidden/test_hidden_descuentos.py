"""Tests ocultos: descuentos por volumen, half-up y base imponible."""

import pytest
from facturacion.modelos import Linea
from facturacion.totales import (
    base_imponible_cents,
    descuento_cents,
    descuento_por_volumen_pct,
)


def test_umbrales_incluyentes_de_volumen():
    assert descuento_por_volumen_pct(0) == 0
    assert descuento_por_volumen_pct(4) == 0
    assert descuento_por_volumen_pct(5) == 5
    assert descuento_por_volumen_pct(9) == 5
    assert descuento_por_volumen_pct(10) == 10
    assert descuento_por_volumen_pct(99) == 10


def test_descuento_cents_half_up():
    assert descuento_cents(1050, 25) == 263  # 262.5 -> 263
    assert descuento_cents(50, 1) == 1      # 0.5 -> 1
    assert descuento_cents(49, 1) == 0      # 0.49 -> 0
    assert descuento_cents(100, 1) == 1     # 1.0 exacto
    assert descuento_cents(0, 25) == 0


def test_base_con_cinco_lineas_y_extra():
    lineas = [Linea("ejemplar", 1, 210)] * 5
    assert base_imponible_cents(lineas, descuento_extra_pct=20) == 787


def test_base_con_diez_lineas():
    lineas = [Linea("ejemplar", 1, 100)] * 10
    assert base_imponible_cents(lineas) == 900


def test_base_sin_descuento_por_debajo_del_umbral():
    lineas = [Linea("a", 1, 300), Linea("b", 2, 100)]
    assert base_imponible_cents(lineas) == 500


def test_descuento_total_mayor_100():
    lineas = [Linea("a", 1, 100)] * 5
    with pytest.raises(ValueError, match="descuento total invalido: 101"):
        base_imponible_cents(lineas, descuento_extra_pct=96)
