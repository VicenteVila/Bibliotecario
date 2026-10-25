"""Modelos de rutas."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Arista:
    origen: str
    destino: str
    coste: int


@dataclass(frozen=True)
class Resultado:
    coste: int
    camino: tuple[str, ...]
