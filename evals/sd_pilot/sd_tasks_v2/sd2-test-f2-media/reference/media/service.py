"""Servicio de playlist."""

from __future__ import annotations

from collections.abc import Sequence

from media.models import Cancion, Resultado
from media.rules import seleccionar


def procesar(
    canciones: Sequence[Cancion], max_segundos: int
) -> Resultado:
    return seleccionar(canciones, max_segundos)
