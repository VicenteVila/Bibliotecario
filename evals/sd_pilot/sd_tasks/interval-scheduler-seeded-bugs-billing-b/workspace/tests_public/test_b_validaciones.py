"""Tests públicos: validaciones de entrada y cliente exento."""

import pytest
from facturacion.emitir import Emisor, emitir
from facturacion.modelos import Cliente, Linea
from facturacion.totales import subtotal_cents


def test_cantidad_no_positiva():
    with pytest.raises(ValueError, match="cantidad no positiva: 0"):
        subtotal_cents([Linea("mala", 0, 100)])


def test_precio_negativo():
    with pytest.raises(ValueError, match="precio negativo: -1"):
        subtotal_cents([Linea("mala", 1, -1)])


def test_emitir_sin_lineas():
    with pytest.raises(ValueError, match="sin lineas"):
        emitir(Emisor(), Cliente("B-1", "Beta"), [], anio=2024)


def test_cliente_exento_no_paga_iva():
    emisor = Emisor()
    cliente = Cliente("E-1", "Exenta", exento_iva=True)
    factura = emitir(
        emisor, cliente, [Linea("curso", 1, 10000)], anio=2024
    )
    assert factura.iva_cents == 0
    assert factura.total_cents == factura.base_cents
