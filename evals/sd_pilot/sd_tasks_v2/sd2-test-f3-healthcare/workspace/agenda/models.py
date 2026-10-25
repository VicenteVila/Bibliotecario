"""Modelos de agenda médica."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cita:
    cita_id: str
    prioridad: int
    status: str = "pending"


@dataclass(frozen=True)
class Resultado:
    asignadas: tuple[tuple[str, int], ...]
    pendientes: int
