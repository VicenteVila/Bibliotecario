"""Tests ocultos: semántica de evaluación, tipos y errores del contrato."""

import pytest
from mini_dsl import ErrorDeSintaxis, ejecutar


def test_division_entre_cero_en_posicion_del_operador():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("1 / 0")
    assert str(excinfo.value) == "error(L1,C3): division entre cero"


def test_division_entre_cero_float():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("4 / 0.0")
    assert str(excinfo.value) == "error(L1,C3): division entre cero"


def test_tipo_invalido_suma_mezclada():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar('"a" + 1')
    assert str(excinfo.value) == (
        "error(L1,C5): tipo invalido para operador +: cadena + numero"
    )


def test_tipo_invalido_booleanos_en_suma():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("verdadero + 1")
    assert str(excinfo.value) == (
        "error(L1,C11): tipo invalido para operador +: booleano + numero"
    )


def test_tipo_invalido_comparacion_mezclada():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar('1 < "a"')
    assert str(excinfo.value) == (
        "error(L1,C3): tipo invalido para operador <: numero < cadena"
    )


def test_tipo_invalido_igualdad_booleano_numero():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("verdadero == 1")
    assert str(excinfo.value) == (
        "error(L1,C11): tipo invalido para operador ==: booleano == numero"
    )


def test_condicion_no_booleana():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("si 1 entonces 2 sino 3")
    assert str(excinfo.value) == (
        "error(L1,C1): la condicion de 'si' debe ser booleana, es numero"
    )


def test_condicion_cadena_no_booleana():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar('si "x" entonces 2 sino 3')
    assert str(excinfo.value) == (
        "error(L1,C1): la condicion de 'si' debe ser booleana, es cadena"
    )


def test_si_anidado_en_condicion():
    assert ejecutar(
        "si si falso entonces verdadero sino falso entonces 20 sino 30"
    ) == [30]


def test_concatenacion_de_cadenas_con_escapes():
    assert ejecutar('let a = "x\\"" \na + "\\\\"') == [None, 'x"\\']


def test_comparacion_lexicografica_de_cadenas():
    assert ejecutar('si "a" < "b" entonces 1 sino 2') == [1]


def test_booleanos_como_valores_y_false_menor_que_true():
    assert ejecutar("let b = falso\nsi b < verdadero entonces 1 sino 2") == [
        None,
        1,
    ]


def test_igualdad_numerica_int_float():
    assert ejecutar("2.0 == 2") == [True]


def test_igualdad_desigual_de_cadenas():
    assert ejecutar('let s = "a"\ns != "b"') == [None, True]


def test_enteros_y_decimales_se_evaluan():
    assert ejecutar("3 + 2.5") == [5.5]


def test_entorno_nuevo_por_llamada():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        ejecutar("y")
    assert str(excinfo.value) == "error(L1,C1): variable no definida: y"


def test_programa_vacio_y_solo_comentarios():
    assert ejecutar("") == []
    assert ejecutar("  \n\n# nada\n   ") == []
