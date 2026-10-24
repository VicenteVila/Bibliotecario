"""Recibo del checkout: formato exacto de importes, tasas y texto final."""

from __future__ import annotations

from decimal import Decimal

from checkout.modelos import Pedido
from checkout.redondeo import a_decimal, redondear
from checkout.totales import (
    desglose_impuestos,
    importe_linea,
    subtotal,
    total_pedido,
)

__all__ = ["formato_importe", "formato_tasa", "recibo"]


def formato_importe(valor: Decimal, decimales: int = 2) -> str:
    """Importe con EXACTAMENTE ``decimales`` dígitos y punto como separador.

    El cero se escribe siempre sin signo: ``-0.00`` se normaliza a ``0.00``.
    """
    cantidad = redondear(valor, decimales)
    if cantidad == 0:
        cantidad = redondear(Decimal(0), decimales)
    texto = str(cantidad)
    if "." in texto:
        parte_entera, parte_decimal = texto.split(".", 1)
        texto = f"{parte_entera}.{parte_decimal.ljust(decimales, '0')}"
    elif decimales > 0:
        texto = f"{texto}.{'0' * decimales}"
    return texto


def formato_tasa(tasa_pct: Decimal | str | int) -> str:
    """Tasa en notación simple: ``21``, ``10.5``, ``0`` (sin ceros sobrantes)."""
    tasa = a_decimal(tasa_pct)
    texto = format(tasa, "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    if texto in ("", "-", "."):
        texto = "0"
    return texto


def recibo(pedido: Pedido) -> str:
    """Recibo en texto plano. Las líneas se unen con ``\\n`` SIN salto final."""
    if not pedido.lineas:
        raise ValueError("sin lineas")
    decimales = pedido.decimales
    cabecera = f"PEDIDO {pedido.identificador}"
    lineas = [cabecera, "=" * len(cabecera)]
    for linea in pedido.lineas:
        precio = formato_importe(linea.precio_unitario, decimales)
        importe = formato_importe(importe_linea(linea, decimales), decimales)
        lineas.append(f"{linea.descripcion} x{linea.cantidad} @{precio} = {importe}")
    lineas.append(f"SUBTOTAL {formato_importe(subtotal(pedido), decimales)}")
    for impuesto, importe in desglose_impuestos(pedido):
        tasa = formato_tasa(impuesto.tasa_pct)
        lineas.append(
            f"{impuesto.nombre} {tasa}% {formato_importe(importe, decimales)}"
        )
    lineas.append(f"TOTAL {formato_importe(total_pedido(pedido), decimales)}")
    return "\n".join(lineas)
