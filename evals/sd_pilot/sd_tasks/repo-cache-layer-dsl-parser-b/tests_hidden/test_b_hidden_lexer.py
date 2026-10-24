"""Tests ocultos: lexer, tokens y errores léxicos con formato exacto."""

import pytest
from mini_dsl import ErrorDeSintaxis, Token, tokenizar


def test_tokenizar_estructura_basica():
    tokens = tokenizar("let x = 1")
    assert tokens == [
        Token("PALABRA", "let", 1, 1),
        Token("IDENT", "x", 1, 5),
        Token("OP", "=", 1, 7),
        Token("NUM", "1", 1, 9),
    ]


def test_tokenizar_lineas_y_columnas():
    tokens = tokenizar("1\n 2")
    assert tokens == [
        Token("NUM", "1", 1, 1),
        Token("NL", "\n", 1, 2),
        Token("NUM", "2", 2, 2),
    ]


def test_tokenizar_comparadores_largos():
    tokens = tokenizar("a <= b == c != d >= e")
    ops = [t.lexema for t in tokens if t.tipo == "OP"]
    assert ops == ["<=", "==", "!=", ">="]


def test_token_inesperado():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar("1 @")
    assert str(excinfo.value) == "error(L1,C3): token inesperado: '@'"


def test_palabras_claves_son_tipo_palabra():
    tokens = tokenizar("si entonces sino verdadero falso")
    assert all(t.tipo == "PALABRA" for t in tokens)


def test_numero_mal_formado_con_letras():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar("12abc")
    assert str(excinfo.value) == "error(L1,C1): numero mal formado: 12abc"


def test_numero_mal_formado_con_dos_puntos():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar("1.2.3 + 1")
    assert str(excinfo.value) == "error(L1,C1): numero mal formado: 1.2.3"


def test_cadena_sin_cerrar_por_fin_de_texto():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar('"hola')
    assert str(excinfo.value) == "error(L1,C1): cadena sin cerrar"


def test_cadena_sin_cerrar_por_salto_de_linea():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar('"hola\n"')
    assert str(excinfo.value) == "error(L1,C1): cadena sin cerrar"


def test_escape_invalido_en_posicion_de_la_barra():
    with pytest.raises(ErrorDeSintaxis) as excinfo:
        tokenizar('"a\\qb"')
    assert str(excinfo.value) == "error(L1,C3): escape invalido: \\q"


def test_escapes_validos_y_lexema_crudo():
    tokens = tokenizar('"a\\"b\\\\c"')
    assert tokens == [Token("CADENA", 'a\\"b\\\\c', 1, 1)]


def test_comentario_no_genera_tokens():
    assert tokenizar("1 # let x =") == [Token("NUM", "1", 1, 1)]
