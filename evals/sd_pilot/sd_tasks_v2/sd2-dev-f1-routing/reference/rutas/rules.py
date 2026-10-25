"""Reglas de rutas."""

from __future__ import annotations

import heapq
from collections.abc import Sequence

from rutas.models import Arista, Resultado


def _validate(
    aristas: Sequence[Arista], inicio: str, fin: str
) -> None:
    if not aristas:
        raise ValueError("grafo vacio")
    nodos: set[str] = set()
    for arista in aristas:
        if arista.coste < 0:
            raise ValueError(
                f"coste invalido: {arista.origen}->{arista.destino}"
            )
        nodos.add(arista.origen)
        nodos.add(arista.destino)
    if inicio not in nodos:
        raise ValueError(f"nodo desconocido: {inicio}")
    if fin not in nodos:
        raise ValueError(f"nodo desconocido: {fin}")


def ruta(
    aristas: Sequence[Arista], inicio: str, fin: str
) -> Resultado:
    _validate(aristas, inicio, fin)
    if inicio == fin:
        return Resultado(0, (inicio,))
    adyacencia: dict[str, list[tuple[str, int]]] = {}
    for arista in aristas:
        adyacencia.setdefault(arista.origen, []).append(
            (arista.destino, arista.coste)
        )
    heap: list[tuple[int, tuple[str, ...], str]] = [
        (0, (inicio,), inicio)
    ]
    vistos: set[str] = set()
    while heap:
        coste, camino, nodo = heapq.heappop(heap)
        if nodo in vistos:
            continue
        vistos.add(nodo)
        if nodo == fin:
            return Resultado(coste, camino)
        for destino, peso in adyacencia.get(nodo, []):
            if destino not in vistos:
                heapq.heappush(
                    heap,
                    (coste + peso, camino + (destino,), destino),
                )
    raise ValueError("sin ruta")
