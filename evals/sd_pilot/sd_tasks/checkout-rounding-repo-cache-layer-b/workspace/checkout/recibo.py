"""Recibo del checkout: formato de importes y texto final."""

from __future__ import annotations

from decimal import Decimal

from checkout.modelos import Pedido
from checkout.redondeo import a_decimal
from checkout.totales import (
    desglose_impuestos,
    importe_linea,
    subtotal,
    total_pedido,
)

__all__ = ["formato_importe", "formato_tasa", "recibo"]


def formato_importe(valor: Decimal, decimales: int = 2) -> str:
    """Representación de un importe."""
    return str(a_decimal(valor))


def formato_tasa(tasa_pct: Decimal | str | int) -> str:
    """Representación de una tasa porcentual."""
    return str(a_decimal(tasa_pct))


def recibo(pedido: Pedido) -> str:
    """Recibo en texto plano."""
    decimales = pedido.decimales
    cabecera = f"PEDIDO {pedido.identificador}"
    lineas = [cabecera, "=" * len(cabecera)]
    for linea in pedido.lineas:
        precio = formato_importe(a_decimal(linea.precio_unitario), decimales)
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
