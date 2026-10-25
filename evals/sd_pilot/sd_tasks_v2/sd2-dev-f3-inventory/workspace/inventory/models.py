"""Modelos del inventario."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Producto:
    sku: str
    nombre: str
    stock: int
    reorder_level: int


@dataclass(frozen=True)
class Reserva:
    sku: str
    cantidad: int
    created_at: int
    ttl_seconds: int
    status: str = "active"
