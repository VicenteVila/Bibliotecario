"""Tests públicos del pipeline de facturación (fallan con los defectos actuales)."""


from facturacion.emitir import Emisor, emitir
from facturacion.impuestos import iva_cents
from facturacion.modelos import Cliente, Linea
from facturacion.totales import base_imponible_cents, descuento_por_volumen_pct


def test_descuento_por_volumen_cinco_lineas():
    assert descuento_por_volumen_pct(5) == 5


def test_base_con_volumen_y_extra_half_up():
    lineas = [Linea("ejemplar", 1, 210)] * 5
    assert base_imponible_cents(lineas, descuento_extra_pct=20) == 787


def test_iva_half_up_en_terminacion_5():
    assert iva_cents(1250) == 263


def test_folio_de_la_primera_factura():
    emisor = Emisor()
    cliente = Cliente("B-1", "Beta")
    factura = emitir(emisor, cliente, [Linea("curso", 1, 10000)], anio=2024)
    assert factura.folio == "F-2024-0001"


def test_factura_completa_referencia():
    emisor = Emisor()
    cliente = Cliente("B-1", "Beta")
    factura = emitir(emisor, cliente, [Linea("curso", 1, 10000)], anio=2024)
    assert factura.subtotal_cents == 10000
    assert factura.descuento_pct == 0
    assert factura.base_cents == 10000
    assert factura.iva_cents == 2100
    assert factura.total_cents == 12100
