"""Recursos disponibles para el agendado."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Recurso:
    nombre: str
    capacidad: int
