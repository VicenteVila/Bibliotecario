"""Modelos de playlist."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cancion:
    cancion_id: str
    segundos: int
    licencia: str = "libre"


@dataclass(frozen=True)
class Resultado:
    seleccion: tuple[str, ...]
    total_segundos: int
    descartadas: int
