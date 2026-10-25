"""Servicio de rutas."""

from __future__ import annotations

from collections.abc import Sequence

from rutas.models import Arista, Resultado
from rutas.rules import ruta


def procesar(
    aristas: Sequence[Arista], inicio: str, fin: str
) -> Resultado:
    return ruta(aristas, inicio, fin)
