"""Modelos de datos del agendado."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intervalo:
    identificador: str
    inicio: int
    fin: int
    prioridad: int = 0

    @property
    def duracion(self) -> int:
        return self.fin - self.inicio


@dataclass(frozen=True)
class Asignacion:
    intervalo: Intervalo
    recurso: str


@dataclass(frozen=True)
class Rechazo:
    intervalo: Intervalo
    motivo: str


@dataclass(frozen=True)
class Plan:
    asignaciones: tuple[Asignacion, ...]
    rechazados: tuple[Rechazo, ...]
    estadisticas: dict = field(default_factory=dict)
