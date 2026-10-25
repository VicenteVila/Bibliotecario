"""Servicio de agenda."""

from __future__ import annotations

from collections.abc import Sequence

from agenda.models import Cita, Resultado
from agenda.rules import asignar


def procesar(
    slots: Sequence[int], citas: Sequence[Cita]
) -> Resultado:
    return asignar(slots, citas)
