"""Tests públicos de playlist."""

import pytest
from media.models import Cancion
from media.service import procesar


def test_selecciona_libres():
    canciones = [Cancion("a", 10), Cancion("b", 20)]
    resultado = procesar(canciones, 100)
    assert resultado.seleccion == ("a", "b")
    assert resultado.total_segundos == 30


def test_omite_propietaria():
    canciones = [Cancion("a", 10, "propietaria"), Cancion("b", 20)]
    resultado = procesar(canciones, 100)
    assert resultado.seleccion == ("b",)
    assert resultado.descartadas == 1


def test_licencia_invalida():
    with pytest.raises(ValueError, match="licencia invalida: a"):
        procesar([Cancion("a", 10, "otra")], 100)


def test_duracion_exacta():
    resultado = procesar([Cancion("a", 100)], 100)
    assert resultado.seleccion == ("a",)


def test_no_cabe():
    canciones = [Cancion("a", 60), Cancion("b", 50)]
    resultado = procesar(canciones, 100)
    assert resultado.seleccion == ("a",)
    assert resultado.descartadas == 1


def test_duracion_cero():
    with pytest.raises(ValueError, match="duracion invalida: a"):
        procesar([Cancion("a", 0)], 100)
