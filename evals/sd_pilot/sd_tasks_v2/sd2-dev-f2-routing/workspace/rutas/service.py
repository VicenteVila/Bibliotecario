"""Servicio de rutas pendiente de completar."""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence

from rutas.models import Arista, Resultado


def procesar(
    aristas: Sequence[Arista], inicio: str, fin: str
) -> Resultado:
    adyacencia: dict[str, list[str]] = {}
    for arista in aristas:
        adyacencia.setdefault(arista.origen, []).append(arista.destino)
    cola = deque([(inicio, (inicio,))])
    vistos = {inicio}
    while cola:
        nodo, camino = cola.popleft()
        if nodo == fin:
            return Resultado(0, camino)
        for destino in adyacencia.get(nodo, []):
            if destino not in vistos:
                vistos.add(destino)
                cola.append((destino, camino + (destino,)))
    return Resultado(0, ())
