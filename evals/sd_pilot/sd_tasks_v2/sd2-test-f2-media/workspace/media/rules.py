"""Reglas de selección de playlist."""

from __future__ import annotations

from collections.abc import Sequence

from media.models import Cancion, Resultado


def _validate(
    canciones: Sequence[Cancion], max_segundos: int
) -> None:
    if max_segundos < 0:
        raise ValueError("maximo invalido")
    for cancion in canciones:
        if cancion.segundos <= 0:
            raise ValueError(f"duracion invalida: {cancion.cancion_id}")
        if cancion.licencia not in {"libre", "cc", "propietaria"}:
            raise ValueError(f"licencia invalida: {cancion.cancion_id}")


def seleccionar(
    canciones: Sequence[Cancion], max_segundos: int
) -> Resultado:
    _validate(canciones, max_segundos)
    seleccion: list[str] = []
    total = 0
    for cancion in canciones:
        if (
            cancion.licencia in {"libre", "cc"}
            and total + cancion.segundos <= max_segundos
        ):
            seleccion.append(cancion.cancion_id)
            total += cancion.segundos
    return Resultado(
        seleccion=tuple(seleccion),
        total_segundos=total,
        descartadas=len(canciones) - len(seleccion),
    )
