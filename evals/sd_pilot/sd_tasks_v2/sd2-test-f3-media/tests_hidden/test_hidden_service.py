"""Tests ocultos de la fachada de playlist."""

import pytest
from media.models import Cancion
from media.service import Playlist


def test_vacio():
    playlist = Playlist([], 100)
    assert playlist.seleccion() == ()
    assert playlist.total_segundos() == 0
    assert playlist.descartadas() == 0


def test_propietaria():
    playlist = Playlist(
        [Cancion("a", 10, "propietaria"), Cancion("b", 5)], 100
    )
    assert playlist.seleccion() == ("b",)
    assert playlist.descartadas() == 1


def test_cc():
    assert Playlist([Cancion("a", 10, "cc")], 10).seleccion() == ("a",)


def test_orden_entrada():
    playlist = Playlist([Cancion("b", 10), Cancion("a", 10)], 100)
    assert playlist.seleccion() == ("b", "a")


def test_greedy():
    canciones = [
        Cancion("a", 60),
        Cancion("b", 50),
        Cancion("c", 40),
    ]
    playlist = Playlist(canciones, 100)
    assert playlist.seleccion() == ("a", "c")
    assert playlist.total_segundos() == 100


def test_duracion_cero():
    with pytest.raises(ValueError, match="duracion invalida: a"):
        Playlist([Cancion("a", 0)], 100).seleccion()


def test_max_negativo():
    with pytest.raises(ValueError, match="maximo invalido"):
        Playlist([Cancion("a", 1)], -1).seleccion()


def test_todas_propietarias():
    playlist = Playlist(
        [Cancion("a", 1, "propietaria"), Cancion("b", 1, "propietaria")],
        100,
    )
    assert playlist.seleccion() == ()
    assert playlist.descartadas() == 2


def test_cancion_grande():
    assert Playlist([Cancion("a", 101)], 100).seleccion() == ()


def test_procesar_coherente():
    playlist = Playlist([Cancion("a", 10), Cancion("b", 20)], 100)
    resultado = playlist.procesar()
    assert resultado.seleccion == playlist.seleccion()
    assert resultado.total_segundos == playlist.total_segundos()
    assert resultado.descartadas == playlist.descartadas()
