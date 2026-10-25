"""Tests públicos de la fachada de rutas."""

import pytest
from rutas.models import Arista
from rutas.service import Rutas


def test_arista_directa():
    resultado = Rutas([Arista("A", "B", 5)], "A", "B").ruta()
    assert resultado.coste == 5
    assert resultado.camino == ("A", "B")


def test_elige_la_mas_barata():
    aristas = [
        Arista("A", "B", 10),
        Arista("B", "C", 1),
        Arista("A", "C", 20),
    ]
    assert Rutas(aristas, "A", "C").procesar().coste == 11


def test_sin_ruta():
    with pytest.raises(ValueError, match="sin ruta"):
        Rutas([Arista("A", "B", 1)], "B", "A").ruta()


def test_misma_ciudad():
    resultado = Rutas([Arista("A", "B", 1)], "A", "A").ruta()
    assert resultado.camino == ("A",)


def test_coste_negativo():
    with pytest.raises(ValueError, match="coste invalido: A->B"):
        Rutas([Arista("A", "B", -1)], "A", "B").ruta()
