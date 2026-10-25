"""Tests públicos de la fachada de playlist."""

import pytest
from media.models import Cancion
from media.service import Playlist


def _playlist() -> Playlist:
    return Playlist([Cancion("a", 10), Cancion("b", 20)], 100)


def test_seleccion():
    assert _playlist().seleccion() == ("a", "b")


def test_total():
    assert _playlist().total_segundos() == 30


def test_descartadas():
    assert _playlist().descartadas() == 0


def test_procesar():
    resultado = _playlist().procesar()
    assert resultado.seleccion == ("a", "b")


def test_licencia_invalida():
    with pytest.raises(ValueError, match="licencia invalida: a"):
        Playlist([Cancion("a", 10, "otra")], 100).seleccion()
