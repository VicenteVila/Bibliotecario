"""Tests públicos: semántica de errores del DSL (tipo, división, variables)."""

import pytest
from mini_dsl import ErrorDeSintaxis, ejecutar


def test_division_entre_cero():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("1 / 0")
    assert str(excinfo.value) == "error(L1,C3): division entre cero"


def test_variable_no_definida():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("x + 1")
    assert str(excinfo.value) == "error(L1,C1): variable no definida: x"


def test_variable_redefinida():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("let x = 1\nlet x = 2")
    assert str(excinfo.value) == "error(L2,C5): variable redefinida: x"


def test_evaluacion_perezosa_de_ramas():
    assert ejecutar("si verdadero entonces 1 sino (1 / 0)") == [1]
    assert ejecutar("si falso entonces (1 / 0) sino 5") == [5]
