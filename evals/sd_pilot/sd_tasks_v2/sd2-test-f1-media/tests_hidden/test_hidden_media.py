"""Tests ocultos de playlist."""

import pytest
from media.models import Cancion
from media.service import procesar


def test_vacio():
    resultado = procesar([], 100)
    assert resultado.seleccion == ()
    assert resultado.total_segundos == 0
    assert resultado.descartadas == 0


def test_max_cero():
    resultado = procesar([Cancion("a", 1)], 0)
    assert resultado.seleccion == ()
    assert resultado.descartadas == 1


def test_cc_cuenta_como_libre():
    resultado = procesar([Cancion("a", 10, "cc")], 10)
    assert resultado.seleccion == ("a",)


def test_propietaria_no_rompe_total():
    canciones = [
        Cancion("a", 10, "propietaria"),
        Cancion("b", 5),
    ]
    resultado = procesar(canciones, 100)
    assert resultado.total_segundos == 5
    assert resultado.descartadas == 1


def test_orden_de_entrada():
    canciones = [Cancion("b", 10), Cancion("a", 10)]
    assert procesar(canciones, 100).seleccion == ("b", "a")


def test_greedy_salta_y_sigue():
    canciones = [
        Cancion("a", 60),
        Cancion("b", 50),
        Cancion("c", 40),
    ]
    resultado = procesar(canciones, 100)
    assert resultado.seleccion == ("a", "c")
    assert resultado.total_segundos == 100


def test_duracion_negativa():
    with pytest.raises(ValueError, match="duracion invalida: a"):
        procesar([Cancion("a", -1)], 100)


def test_max_negativo():
    with pytest.raises(ValueError, match="maximo invalido"):
        procesar([Cancion("a", 1)], -1)


def test_licencia_mayusculas_invalida():
    with pytest.raises(ValueError, match="licencia invalida: a"):
        procesar([Cancion("a", 1, "Libre")], 100)


def test_todas_propietarias():
    canciones = [
        Cancion("a", 1, "propietaria"),
        Cancion("b", 1, "propietaria"),
    ]
    resultado = procesar(canciones, 100)
    assert resultado.seleccion == ()
    assert resultado.descartadas == 2


def test_cancion_grande_no_entra():
    resultado = procesar([Cancion("a", 101)], 100)
    assert resultado.seleccion == ()


def test_total_coincide_con_seleccion():
    canciones = [Cancion("a", 10), Cancion("b", 20), Cancion("c", 30)]
    resultado = procesar(canciones, 100)
    assert resultado.total_segundos == 60
