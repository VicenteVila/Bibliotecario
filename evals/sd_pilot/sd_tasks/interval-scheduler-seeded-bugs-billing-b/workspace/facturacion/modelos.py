"""Modelos de la facturación (correctos; no contienen defectos)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cliente:
    cif: str
    nombre: str
    exento_iva: bool = False


@dataclass(frozen=True)
class Linea:
    descripcion: str
    cantidad: int
    precio_unit_cents: int


@dataclass(frozen=True)
class Factura:
    cliente: Cliente
    lineas: tuple[Linea, ...]
    folio: str
    anio: int
    subtotal_cents: int
    descuento_pct: int
    base_cents: int
    iva_cents: int
    total_cents: int
