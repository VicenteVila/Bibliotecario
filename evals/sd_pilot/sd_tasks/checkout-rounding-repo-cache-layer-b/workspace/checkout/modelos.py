"""Modelos del checkout: línea de pedido y pedido completo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from checkout.impuestos import Impuesto

__all__ = ["LineaPedido", "Pedido"]


@dataclass(frozen=True)
class LineaPedido:
    descripcion: str
    cantidad: int
    precio_unitario: Decimal | str | int


@dataclass(frozen=True)
class Pedido:
    identificador: str
    lineas: tuple[LineaPedido, ...]
    impuestos: tuple[Impuesto, ...] = ()
    decimales: int = 2
