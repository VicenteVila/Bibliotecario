"""Fachada de rutas."""

from __future__ import annotations

from collections.abc import Sequence

from rutas.models import Arista, Resultado
from rutas.rules import ruta


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
        return ruta(self._aristas, self._inicio, self._fin)

    def procesar(self) -> Resultado:
        return self.ruta()
