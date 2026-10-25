"""Tests ocultos de rutas."""

import pytest
from rutas.models import Arista
from rutas.service import procesar


def test_misma_ciudad():
    resultado = procesar([Arista("A", "B", 1)], "A", "A")
    assert resultado.coste == 0
    assert resultado.camino == ("A",)


def test_nodo_desconocido_inicio():
    with pytest.raises(ValueError, match="nodo desconocido: X"):
        procesar([Arista("A", "B", 1)], "X", "B")


def test_nodo_desconocido_fin():
    with pytest.raises(ValueError, match="nodo desconocido: X"):
        procesar([Arista("A", "B", 1)], "A", "X")


def test_camino_con_dos_aristas():
    aristas = [Arista("A", "B", 2), Arista("B", "C", 3)]
    resultado = procesar(aristas, "A", "C")
    assert resultado.coste == 5
    assert resultado.camino == ("A", "B", "C")


def test_ignora_ciclos():
    aristas = [
        Arista("A", "B", 1),
        Arista("B", "A", 1),
        Arista("B", "C", 1),
    ]
    assert procesar(aristas, "A", "C").coste == 2


def test_paralelas_elige_menor():
    aristas = [Arista("A", "B", 9), Arista("A", "B", 3)]
    assert procesar(aristas, "A", "B").coste == 3


def test_desempate_lexicografico():
    aristas = [
        Arista("A", "C", 1),
        Arista("C", "D", 1),
        Arista("A", "B", 1),
        Arista("B", "D", 1),
    ]
    assert procesar(aristas, "A", "D").camino == ("A", "B", "D")


def test_coste_grande():
    aristas = [Arista("A", "B", 10**9)]
    assert procesar(aristas, "A", "B").coste == 10**9


def test_arista_aislada_no_estorba():
    aristas = [
        Arista("A", "B", 1),
        Arista("X", "Y", 1),
    ]
    assert procesar(aristas, "A", "B").coste == 1


def test_ruta_mas_larga_es_mas_barata():
    aristas = [
        Arista("A", "B", 1),
        Arista("B", "C", 1),
        Arista("C", "D", 1),
        Arista("A", "D", 10),
    ]
    assert procesar(aristas, "A", "D").coste == 3


def test_sin_ruta_entre_componentes():
    aristas = [Arista("A", "B", 1), Arista("C", "D", 1)]
    with pytest.raises(ValueError, match="sin ruta"):
        procesar(aristas, "A", "D")


def test_autociclo_no_afecta():
    aristas = [Arista("A", "A", 0), Arista("A", "B", 2)]
    assert procesar(aristas, "A", "B").coste == 2
