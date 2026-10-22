"""Tests ocultos: límite de profundidad de anidamiento (paréntesis y si)."""

import pytest
from mini_dsl import ErrorDeSintaxis, ejecutar


def test_profundidad_32_de_parentesis_es_valida():
    texto = "(" * 32 + "1" + ")" * 32
    assert ejecutar(texto) == [1]


def test_profundidad_33_de_parentesis_falla_en_el_token_abridor():
    texto = "(" * 33 + "1" + ")" * 33
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar(texto)
    assert str(excinfo.value) == (
        "error(L1,C33): profundidad maxima excedida (maxima: 32)"
    )


def test_profundidad_32_de_si_es_valida():
    expr = "1"
    for _ in range(32):
        expr = f"si verdadero entonces {expr} sino 0"
    assert ejecutar(expr) == [1]


def test_profundidad_33_de_si_falla_en_el_si_mas_interno():
    expr = "1"
    for _ in range(33):
        expr = f"si verdadero entonces {expr} sino 0"
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar(expr)
    posicion_si_interno = expr.rfind("si ") + 1
    assert str(excinfo.value) == (
        f"error(L1,C{posicion_si_interno}): "
        "profundidad maxima excedida (maxima: 32)"
    )


def test_profundidad_mixta_parentesis_y_si():
    expr = "1"
    for _ in range(20):
        expr = f"({expr} + 0)"
    for _ in range(12):
        expr = f"si verdadero entonces {expr} sino 0"
    assert ejecutar(expr) == [1]
