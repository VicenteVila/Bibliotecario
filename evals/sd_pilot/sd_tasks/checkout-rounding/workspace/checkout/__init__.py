"""Pipeline de checkout (versión inicial con redondeo poco fiable)."""

from checkout.impuestos import EXENTO, IVA_GENERAL, IVA_REDUCIDO, Impuesto, importe_impuesto
from checkout.modelos import LineaPedido, Pedido
from checkout.recibo import formato_importe, formato_tasa, recibo
from checkout.redondeo import a_decimal, redondear
from checkout.totales import (
    desglose_impuestos,
    importe_linea,
    subtotal,
    total_impuestos,
    total_pedido,
)

__all__ = [
    "EXENTO",
    "IVA_GENERAL",
    "IVA_REDUCIDO",
    "Impuesto",
    "LineaPedido",
    "Pedido",
    "a_decimal",
    "desglose_impuestos",
    "formato_importe",
    "formato_tasa",
    "importe_impuesto",
    "importe_linea",
    "recibo",
    "redondear",
    "subtotal",
    "total_impuestos",
    "total_pedido",
]
