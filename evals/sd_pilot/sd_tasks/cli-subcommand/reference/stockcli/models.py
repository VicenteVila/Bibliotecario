"""Modelos y datos del inventario."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    """Una fila del inventario."""

    sku: str
    qty: int
    status: str


@dataclass(frozen=True)
class ReportResult:
    """Resultado del comando report."""

    total: int
    rows: tuple[Item, ...]


ITEMS: tuple[Item, ...] = (
    Item("TORN-001", 120, "OK"),
    Item("TORN-002", 8, "LOW"),
    Item("CLAV-010", 0, "OUT"),
    Item("CLAV-011", 45, "OK"),
    Item("LIJA-003", 3, "LOW"),
    Item("PIN-077", 200, "OK"),
    Item("PIN-078", 0, "OUT"),
    Item("CIN-001", 17, "LOW"),
    Item("BOX-002", 17, "OK"),
    Item("BOX-001", 60, "OK"),
)
