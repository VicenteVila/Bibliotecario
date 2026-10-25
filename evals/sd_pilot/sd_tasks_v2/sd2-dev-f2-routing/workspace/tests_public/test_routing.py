"""Tests públicos de rutas."""

import pytest
from rutas.models import Arista
from rutas.service import procesar


def test_arista_directa():
    resultado = procesar([Arista("A", "B", 5)], "A", "B")
    assert resultado.coste == 5
    assert resultado.camino == ("A", "B")


def test_elige_la_mas_barata():
    aristas = [
        Arista("A", "B", 10),
        Arista("B", "C", 1),
        Arista("A", "C", 20),
    ]
    resultado = procesar(aristas, "A", "C")
    assert resultado.coste == 11
    assert resultado.camino == ("A", "B", "C")


def test_sin_ruta():
    with pytest.raises(ValueError, match="sin ruta"):
        procesar([Arista("A", "B", 1)], "B", "A")


def test_coste_cero():
    resultado = procesar([Arista("A", "B", 0)], "A", "B")
    assert resultado.coste == 0


def test_coste_negativo():
    with pytest.raises(ValueError, match="coste invalido: A->B"):
        procesar([Arista("A", "B", -1)], "A", "B")


def test_grafo_vacio():
    with pytest.raises(ValueError, match="grafo vacio"):
        procesar([], "A", "B")
