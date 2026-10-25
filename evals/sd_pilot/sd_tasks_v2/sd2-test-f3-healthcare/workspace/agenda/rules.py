"""Reglas de asignación de agenda."""

from __future__ import annotations

from collections.abc import Sequence

from agenda.models import Cita, Resultado


def _validate(slots: Sequence[int], citas: Sequence[Cita]) -> None:
    vistos: set[str] = set()
    for cita in citas:
        if cita.cita_id in vistos:
            raise ValueError(f"cita duplicada: {cita.cita_id}")
        vistos.add(cita.cita_id)
        if not 1 <= cita.prioridad <= 3:
            raise ValueError(f"prioridad invalida: {cita.cita_id}")
    vistos_slots: set[int] = set()
    for slot in slots:
        if slot < 0:
            raise ValueError(f"slot invalido: {slot}")
        if slot in vistos_slots:
            raise ValueError(f"slot duplicado: {slot}")
        vistos_slots.add(slot)


def asignar(
    slots: Sequence[int], citas: Sequence[Cita]
) -> Resultado:
    _validate(slots, citas)
    pendientes = [cita for cita in citas if cita.status == "pending"]
    ordenadas = sorted(
        pendientes, key=lambda cita: (cita.prioridad, cita.cita_id)
    )
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
