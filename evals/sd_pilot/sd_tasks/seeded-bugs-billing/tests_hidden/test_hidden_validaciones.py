"""Tests ocultos: validaciones y redondeo half-up en general."""

import pytest
from facturacion.modelos import Linea
from facturacion.totales import subtotal_cents


def test_cantidad_no_positiva():
    with pytest.raises(ValueError, match="cantidad no positiva: -2"):
        subtotal_cents([Linea("mala", -2, 100)])


def test_precio_negativo():
    with pytest.raises(ValueError, match="precio negativo: -7"):
        subtotal_cents([Linea("mala", 1, -7)])


def test_primera_linea_invalida_gana():
    with pytest.raises(ValueError, match="precio negativo: -1"):
        subtotal_cents(
            [Linea("ok", 1, 100), Linea("mala", 1, -1), Linea("mala2", 0, 1)]
        )


def test_subtotal_suma_correcta():
    lineas = [
        Linea("a", 2, 150),
        Linea("b", 1, 700),
        Linea("c", 10, 33),
    ]
    assert subtotal_cents(lineas) == 300 + 700 + 330


def test_subtotal_vacio_es_cero():
    assert subtotal_cents([]) == 0
