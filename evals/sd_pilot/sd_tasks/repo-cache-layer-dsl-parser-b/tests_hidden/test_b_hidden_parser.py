"""Tests ocultos: errores sintácticos y sus posiciones exactas."""

import pytest
from mini_dsl import ErrorDeSintaxis, ejecutar


def test_fin_de_entrada_tras_operador():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("2 +")
    assert str(excinfo.value) == (
        "error(L1,C4): se esperaba un valor pero llegó fin de entrada"
    )


def test_fin_de_entrada_en_parentesis():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("(1 + 2")
    assert str(excinfo.value) == (
        "error(L1,C7): se esperaba ) pero llegó fin de entrada"
    )


def test_parentesis_con_token_inesperado():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("(1 2)")
    assert str(excinfo.value) == "error(L1,C4): se esperaba ) pero llegó '2'"


def test_let_sin_identificador():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("let 1 = 2")
    assert str(excinfo.value) == (
        "error(L1,C5): se esperaba un identificador pero llegó '1'"
    )


def test_let_identificador_reservado():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("let si = 2")
    assert str(excinfo.value) == "error(L1,C5): identificador reservado: si"


def test_let_sin_operador_igual():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("let x2")
    assert str(excinfo.value) == (
        "error(L1,C7): se esperaba el operador '=' pero llegó fin de entrada"
    )


def test_sentencias_pegadas():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("1 2")
    assert str(excinfo.value) == (
        "error(L1,C3): se esperaba fin de línea pero llegó '2'"
    )


def test_sino_faltante_por_fin_de_entrada():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("si 1 == 1 entonces 1")
    assert str(excinfo.value) == (
        "error(L1,C21): se esperaba una palabra clave 'sino' pero llegó "
        "fin de entrada"
    )


def test_sino_faltante_por_token():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("si verdadero entonces 1 5 sino 2")
    assert str(excinfo.value) == (
        "error(L1,C25): se esperaba una palabra clave 'sino' pero llegó '5'"
    )


def test_entonces_faltante():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("si verdadero 1 sino 2")
    assert str(excinfo.value) == (
        "error(L1,C14): se esperaba una palabra clave 'entonces' pero llegó '1'"
    )


def test_si_no_puede_ir_tras_un_operador():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("1 + si verdadero entonces 1 sino 2")
    assert str(excinfo.value) == "error(L1,C5): token inesperado: 'si'"


def test_salto_de_linea_dentro_de_expresion():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("1 +\n2")
    assert str(excinfo.value) == (
        "error(L1,C4): se esperaba un valor pero llegó '\\n'"
    )
