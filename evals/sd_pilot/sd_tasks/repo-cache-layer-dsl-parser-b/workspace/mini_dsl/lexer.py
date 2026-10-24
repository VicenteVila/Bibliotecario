"""Lexer preliminar: enteros, decimales, identificadores, ops y comentarios."""

from __future__ import annotations

import re

from mini_dsl.errores import ErrorDeSintaxis
from mini_dsl.tokens import Token

_NUM = re.compile(r"[0-9]+(\.[0-9]+)?")
_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_OPERADORES = ["==", "!=", "<=", ">=", "+", "-", "*", "/", "(", ")", "=", "<", ">"]


def tokenizar(texto: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    linea = 1
    columna = 1
    largo = len(texto)
    while i < largo:
        c = texto[i]
        if c == "\n":
            tokens.append(Token("NL", "\n", linea, columna))
            i += 1
            linea += 1
            columna = 1
            continue
        if c in " \t":
            i += 1
            columna += 1
            continue
        if c == "#":
            while i < largo and texto[i] != "\n":
                i += 1
                columna += 1
            continue
        if c.isdigit():
            coincidencia = _NUM.match(texto, i)
            assert coincidencia is not None
            lexema = coincidencia.group(0)
            tokens.append(Token("NUM", lexema, linea, columna))
            i += len(lexema)
            columna += len(lexema)
            continue
        if c.isalpha() or c == "_":
            coincidencia = _IDENT.match(texto, i)
            assert coincidencia is not None
            lexema = coincidencia.group(0)
            tokens.append(Token("IDENT", lexema, linea, columna))
            i += len(lexema)
            columna += len(lexema)
            continue
        op = next((o for o in _OPERADORES if texto.startswith(o, i)), None)
        if op is not None:
            tokens.append(Token("OP", op, linea, columna))
            i += len(op)
            columna += len(op)
            continue
        raise ErrorDeSintaxis(
            f"sintaxis invalida en linea {linea}, columna {columna}"
        )
    return tokens
