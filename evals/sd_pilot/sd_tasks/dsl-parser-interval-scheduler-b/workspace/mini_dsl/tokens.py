"""Tipos de token del mini-DSL."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Token:
    tipo: str
    lexema: str
    linea: int
    columna: int
