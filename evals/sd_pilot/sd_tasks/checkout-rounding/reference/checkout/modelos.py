"""Modelos del checkout: línea de pedido y pedido completo."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from checkout.impuestos import Impuesto
from checkout.redondeo import a_decimal

__all__ = ["LineaPedido", "Pedido"]


@dataclass(frozen=True)
class LineaPedido:
    descripcion: str
    cantidad: int
    precio_unitario: Decimal | str | int

    def __post_init__(self) -> None:
        if not self.descripcion:
            raise ValueError("descripcion vacia")
        if not isinstance(self.cantidad, int) or isinstance(self.cantidad, bool):
            raise TypeError(f"cantidad no entera: {type(self.cantidad).__name__}")
        precio = a_decimal(self.precio_unitario)
        if precio < 0:
            raise ValueError(f"precio negativo: {self.precio_unitario}")
        object.__setattr__(self, "precio_unitario", precio)


@dataclass(frozen=True)
class Pedido:
    identificador: str
    lineas: tuple[LineaPedido, ...]
    impuestos: tuple[Impuesto, ...] = ()
    decimales: int = 2

    def __post_init__(self) -> None:
        if not self.identificador:
            raise ValueError("identificador vacio")
        if not isinstance(self.decimales, int) or isinstance(self.decimales, bool):
            raise TypeError(f"decimales no entero: {type(self.decimales).__name__}")
        if self.decimales < 0:
            raise ValueError(f"decimales invalidos: {self.decimales}")
