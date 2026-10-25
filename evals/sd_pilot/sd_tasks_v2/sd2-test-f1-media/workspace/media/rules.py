"""Reglas de selección de playlist."""

from __future__ import annotations

from collections.abc import Sequence

from media.models import Cancion, Resultado


def seleccionar(
    canciones: Sequence[Cancion], max_segundos: int
) -> Resultado:
    seleccion: list[str] = []
    total = 0
    for cancion in canciones:
        if cancion.licencia == "propietaria":
            continue
        if total + cancion.segundos < max_segundos:
            seleccion.append(cancion.cancion_id)
            total += cancion.segundos
    return Resultado(
        seleccion=tuple(seleccion),
        total_segundos=total,
        descartadas=len(canciones) - len(seleccion),
    )
