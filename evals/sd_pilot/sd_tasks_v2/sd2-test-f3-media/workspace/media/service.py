"""Fachada de playlist pendiente de implementar."""

from __future__ import annotations

from collections.abc import Sequence

from media.models import Cancion, Resultado


class Playlist:
    def __init__(
        self, canciones: Sequence[Cancion], max_segundos: int
    ) -> None:
        self._canciones = tuple(canciones)
        self._max_segundos = max_segundos

    def seleccion(self) -> tuple[str, ...]:
        raise NotImplementedError

    def total_segundos(self) -> int:
        raise NotImplementedError

    def descartadas(self) -> int:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
