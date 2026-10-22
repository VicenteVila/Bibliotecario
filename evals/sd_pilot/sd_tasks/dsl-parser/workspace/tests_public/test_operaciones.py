"""Tests públicos: operaciones básicas, let, comentarios y errores simples."""

import pytest
from mini_dsl import ErrorDeSintaxis, ejecutar


def test_expresion_basica_con_precedencia():
    assert ejecutar("2 + 3 * 4") == [14]


def test_let_y_variable():
    assert ejecutar("let x = 10\nx * 2") == [None, 20]


def test_parentesis():
    assert ejecutar("(2 + 3) * 4") == [20]


def test_comentarios_y_lineas_vacias():
    assert ejecutar("# hola\n\nlet a = 7\na") == [None, 7]


def test_division_devuelve_float():
    assert ejecutar("7 / 2") == [3.5]


def test_error_formato_fin_de_entrada():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("2 +")
    assert str(excinfo.value) == (
        "error(L1,C4): se esperaba un valor pero llegó fin de entrada"
    )


def test_cadena_concatenacion():
    assert ejecutar('let s = "hola"\ns + " mundo"') == [None, "hola mundo"]


def test_si_basico_con_comparacion():
    assert ejecutar('si 1 < 2 entonces "si" sino "no"') == ["si"]
