"""Fachada de rutas pendiente de implementar."""

from __future__ import annotations

from collections.abc import Sequence

from rutas.models import Arista, Resultado


class Rutas:
    def __init__(
        self,
        aristas: Sequence[Arista],
        inicio: str,
        fin: str,
    ) -> None:
        self._aristas = tuple(aristas)
        self._inicio = inicio
        self._fin = fin

    def ruta(self) -> Resultado:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
