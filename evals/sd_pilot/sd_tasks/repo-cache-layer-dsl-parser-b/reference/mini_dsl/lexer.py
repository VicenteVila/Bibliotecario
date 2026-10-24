"""Lexer del mini-DSL. Todos los errores usan el formato `error(L,C): motivo`."""

from __future__ import annotations

import re

from mini_dsl.errores import ErrorDeSintaxis
from mini_dsl.tokens import Token

PALABRAS = frozenset({"let", "si", "entonces", "sino", "verdadero", "falso"})
_NUM_VALIDO = re.compile(r"[0-9]+(\.[0-9]+)?")
_SECUENCIA_NUM = re.compile(r"[0-9A-Za-z_.]+")
_OPERADORES = ("==", "!=", "<=", ">=", "+", "-", "*", "/", "(", ")", "=", "<", ">")


def _error(linea: int, columna: int, motivo: str) -> ErrorDeSintaxis:
    return ErrorDeSintaxis(f"error(L{linea},C{columna}): {motivo}")


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
            coincidencia = _SECUENCIA_NUM.match(texto, i)
            assert coincidencia is not None
            secuencia = coincidencia.group(0)
            if not _NUM_VALIDO.fullmatch(secuencia):
                raise _error(linea, columna, f"numero mal formado: {secuencia}")
            tokens.append(Token("NUM", secuencia, linea, columna))
            i += len(secuencia)
            columna += len(secuencia)
            continue
        if c.isalpha() or c == "_":
            inicio_col = columna
            inicio = i
            while i < largo and (texto[i].isalnum() or texto[i] == "_"):
                i += 1
                columna += 1
            lexema = texto[inicio:i]
            tipo = "PALABRA" if lexema in PALABRAS else "IDENT"
            tokens.append(Token(tipo, lexema, linea, inicio_col))
            continue
        if c == '"':
            linea_ini, col_ini = linea, columna
            i += 1
            columna += 1
            contenido: list[str] = []
            cerrada = False
            while i < largo:
                ch = texto[i]
                if ch == "\n":
                    break
                if ch == "\\":
                    if i + 1 >= largo or texto[i + 1] == "\n":
                        raise _error(linea_ini, col_ini, "cadena sin cerrar")
                    sig = texto[i + 1]
                    if sig not in ('"', "\\"):
                        raise _error(
                            linea, columna, f"escape invalido: \\{sig}"
                        )
                    contenido.append(ch)
                    contenido.append(sig)
                    i += 2
                    columna += 2
                    continue
                if ch == '"':
                    i += 1
                    columna += 1
                    cerrada = True
                    break
                contenido.append(ch)
                i += 1
                columna += 1
            if not cerrada:
                raise _error(linea_ini, col_ini, "cadena sin cerrar")
            tokens.append(
                Token("CADENA", "".join(contenido), linea_ini, col_ini)
            )
            continue
        op = next((o for o in _OPERADORES if texto.startswith(o, i)), None)
        if op is not None:
            tokens.append(Token("OP", op, linea, columna))
            i += len(op)
            columna += len(op)
            continue
        raise _error(linea, columna, f"token inesperado: {c!r}")
    return tokens
