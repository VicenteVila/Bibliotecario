"""Tests ocultos: folios correlativos y emisión completa."""

import pytest
from facturacion.emitir import Emisor, emitir
from facturacion.modelos import Cliente, Linea

CLIENTE = Cliente("B-1", "Beta")


def test_folios_correlativos_desde_uno():
    emisor = Emisor()
    folios = [
        emitir(emisor, CLIENTE, [Linea("x", 1, 100)], anio=2024).folio
        for _ in range(3)
    ]
    assert folios == ["F-2024-0001", "F-2024-0002", "F-2024-0003"]


def test_folios_independientes_por_anio():
    emisor = Emisor()
    assert emitir(emisor, CLIENTE, [Linea("x", 1, 100)], 2024).folio == "F-2024-0001"
    assert emitir(emisor, CLIENTE, [Linea("x", 1, 100)], 2025).folio == "F-2025-0001"
    assert emitir(emisor, CLIENTE, [Linea("x", 1, 100)], 2024).folio == "F-2024-0002"


def test_cliente_exento_con_volumen():
    exenta = Cliente("E-1", "Exenta", exento_iva=True)
    emisor = Emisor()
    lineas = [Linea("ejemplar", 1, 210)] * 5
    factura = emitir(emisor, exenta, lineas, anio=2024)
    assert factura.descuento_pct == 5
    assert factura.subtotal_cents == 1050
    assert factura.base_cents == 997
    assert factura.iva_cents == 0
    assert factura.total_cents == 997


def test_emitir_campos_completos():
    emisor = Emisor()
    factura = emitir(emisor, CLIENTE, [Linea("curso", 1, 10000)], anio=2024)
    assert factura.cliente == CLIENTE
    assert factura.lineas == (Linea("curso", 1, 10000),)
    assert factura.anio == 2024
    assert factura.folio == "F-2024-0001"
    assert factura.subtotal_cents == 10000
    assert factura.descuento_pct == 0
    assert factura.base_cents == 10000
    assert factura.iva_cents == 2100
    assert factura.total_cents == 12100


def test_emitir_no_toma_folio_si_las_lineas_son_invalidas():
    emisor = Emisor()
    with pytest.raises(ValueError, match="cantidad no positiva: 0"):
        emitir(emisor, CLIENTE, [Linea("mala", 0, 100)], anio=2024)
    assert emitir(emisor, CLIENTE, [Linea("x", 1, 100)], 2024).folio == "F-2024-0001"


def test_pipeline_lote_mezclado():
    emisor = Emisor()
    f1 = emitir(emisor, CLIENTE, [Linea("a", 1, 250)] * 4, anio=2024)
    f2 = emitir(emisor, CLIENTE, [Linea("b", 1, 210)] * 5, anio=2024)
    assert f1.folio == "F-2024-0001"
    assert f1.total_cents == 1210
    assert f2.folio == "F-2024-0002"
    assert f2.descuento_pct == 5
    assert f2.base_cents == 997
    assert f2.iva_cents == 209
    assert f2.total_cents == 1206
