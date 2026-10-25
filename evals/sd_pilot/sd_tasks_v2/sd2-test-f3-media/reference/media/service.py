"""Fachada de playlist."""

from __future__ import annotations

from collections.abc import Sequence

from media.models import Cancion, Resultado
from media.rules import seleccionar


class Playlist:
    def __init__(
        self, canciones: Sequence[Cancion], max_segundos: int
    ) -> None:
        self._canciones = tuple(canciones)
        self._max_segundos = max_segundos

    def seleccion(self) -> tuple[str, ...]:
        return seleccionar(
            self._canciones, self._max_segundos
        ).seleccion

    def total_segundos(self) -> int:
        return seleccionar(
            self._canciones, self._max_segundos
        ).total_segundos

    def descartadas(self) -> int:
        return seleccionar(
            self._canciones, self._max_segundos
        ).descartadas

    def procesar(self) -> Resultado:
        return seleccionar(self._canciones, self._max_segundos)
