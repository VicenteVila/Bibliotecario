"""Reglas de asignación de agenda."""

from __future__ import annotations

from collections.abc import Sequence

from agenda.models import Cita, Resultado


def asignar(
    slots: Sequence[int], citas: Sequence[Cita]
) -> Resultado:
    pendientes = [cita for cita in citas if cita.status == "pending"]
    ordenadas = sorted(pendientes, key=lambda cita: cita.cita_id)
    disponibles = sorted(slots)
    asignadas = tuple(
        zip(
            (cita.cita_id for cita in ordenadas),
            disponibles,
        )
    )
    return Resultado(
        asignadas=asignadas,
        pendientes=max(0, len(ordenadas) - len(disponibles)),
    )
