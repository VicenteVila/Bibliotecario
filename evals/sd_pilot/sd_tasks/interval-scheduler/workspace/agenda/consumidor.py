"""Coordinador de sala única: módulo consumidor existente del planificador.

No se toca: define la semántica observable que el planificador debe
respetar (claves de estadísticas, determinismo, entradas vacías).
"""

from __future__ import annotations

from collections.abc import Iterable

from agenda.modelo import Intervalo, Plan
from agenda.planificador import planificar
from agenda.recurso import Recurso

NOMBRE_SALA = "sala"


class CoordinadorSala:
    def __init__(self, capacidad: int) -> None:
        self._recurso = Recurso(NOMBRE_SALA, capacidad)

    def programar(
        self,
        intervalos: Iterable[Intervalo],
        desde: int | None = None,
        hasta: int | None = None,
    ) -> Plan:
        ventana: tuple[int, int] | None = None
        if desde is not None and hasta is not None:
            ventana = (desde, hasta)
        return planificar(intervalos, [self._recurso], ventana=ventana)

    def resumen(self, plan: Plan) -> dict[str, int]:
        estadisticas = plan.estadisticas
        return {
            "ocupacion_maxima": estadisticas["uso_por_recurso"].get(
                NOMBRE_SALA, 0
            ),
            "asignados": estadisticas["asignados"],
            "rechazados": estadisticas["rechazados"],
        }
