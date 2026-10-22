"""Modelos de dominio del catálogo. Inmutables y sin dependencias externas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Libro:
    isbn: str
    titulo: str
    autor: str
    anio: int
    copias: int


@dataclass(frozen=True)
class Prestamo:
    identificador: str
    isbn: str
    lector: str
    activo: bool
