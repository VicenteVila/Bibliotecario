"""Tests ocultos de la fachada de rutas."""

import pytest
from rutas.models import Arista
from rutas.service import Rutas


def test_grafo_vacio():
    with pytest.raises(ValueError, match="grafo vacio"):
        Rutas([], "A", "B").ruta()


def test_nodo_desconocido():
    with pytest.raises(ValueError, match="nodo desconocido: X"):
        Rutas([Arista("A", "B", 1)], "A", "X").ruta()


def test_camino_dos_aristas():
    aristas = [Arista("A", "B", 2), Arista("B", "C", 3)]
    assert Rutas(aristas, "A", "C").ruta().coste == 5


def test_paralelas():
    aristas = [Arista("A", "B", 9), Arista("A", "B", 3)]
    assert Rutas(aristas, "A", "B").ruta().coste == 3


def test_desempate():
    aristas = [
        Arista("A", "C", 1),
        Arista("C", "D", 1),
        Arista("A", "B", 1),
        Arista("B", "D", 1),
    ]
    assert Rutas(aristas, "A", "D").ruta().camino == ("A", "B", "D")


def test_ciclo():
    aristas = [
        Arista("A", "B", 1),
        Arista("B", "A", 1),
        Arista("B", "C", 1),
    ]
    assert Rutas(aristas, "A", "C").ruta().coste == 2


def test_coste_grande():
    aristas = [Arista("A", "B", 10**9)]
    assert Rutas(aristas, "A", "B").ruta().coste == 10**9


def test_componentes_desconectadas():
    aristas = [Arista("A", "B", 1), Arista("C", "D", 1)]
    with pytest.raises(ValueError, match="sin ruta"):
        Rutas(aristas, "A", "D").ruta()


def test_ruta_larga_mas_barata():
    aristas = [
        Arista("A", "B", 1),
        Arista("B", "C", 1),
        Arista("C", "D", 1),
        Arista("A", "D", 10),
    ]
    assert Rutas(aristas, "A", "D").ruta().coste == 3


def test_procesar_igual_a_ruta():
    rutas = Rutas([Arista("A", "B", 5)], "A", "B")
    assert rutas.procesar() == rutas.ruta()
