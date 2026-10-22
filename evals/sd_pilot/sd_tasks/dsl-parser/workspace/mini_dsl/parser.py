"""Parser preliminar: let, aritmética con paréntesis. Sin si/cadenas/comparaciones."""

from __future__ import annotations

from mini_dsl import nodos
from mini_dsl.errores import ErrorDeSintaxis
from mini_dsl.lexer import tokenizar
from mini_dsl.tokens import Token


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._i = 0

    def _actual(self) -> Token | None:
        if self._i < len(self._tokens):
            return self._tokens[self._i]
        return None

    def _avanzar(self) -> Token:
        token = self._tokens[self._i]
        self._i += 1
        return token

    def _fallo(self, token: Token | None, mensaje: str) -> ErrorDeSintaxis:
        if token is None:
            return ErrorDeSintaxis(f"sintaxis invalida al final: {mensaje}")
        return ErrorDeSintaxis(
            f"sintaxis invalida en linea {token.linea}, columna {token.columna}"
            f": {mensaje}"
        )

    def parsear_programa(self) -> nodos.Programa:
        sentencias: list = []
        while self._actual() is not None:
            while self._actual() is not None and self._actual().tipo == "NL":
                self._avanzar()
            if self._actual() is None:
                break
            sentencias.append(self._parsear_sentencia())
        return nodos.Programa(sentencias=tuple(sentencias))

    def _parsear_sentencia(self):
        token = self._actual()
        if token is not None and token.tipo == "IDENT" and token.lexema == "let":
            self._avanzar()
            nombre = self._avanzar()
            if nombre.tipo != "IDENT":
                raise self._fallo(nombre, "falta el nombre de la variable")
            igual = self._actual()
            if igual is None or igual.tipo != "OP" or igual.lexema != "=":
                raise self._fallo(igual, "falta el '=' de asignacion")
            self._avanzar()
            expr = self._parsear_expr()
            return nodos.Definicion(nombre.lexema, expr, nombre)
        return nodos.Expresion(self._parsear_expr())

    def _parsear_expr(self):
        return self._parsear_suma()

    def _parsear_suma(self):
        izq = self._parsear_producto()
        while (
            self._actual() is not None
            and self._actual().tipo == "OP"
            and self._actual().lexema in ("+", "-")
        ):
            op = self._avanzar()
            der = self._parsear_producto()
            izq = nodos.Binaria(izq, op.lexema, der, op)
        return izq

    def _parsear_producto(self):
        izq = self._parsear_primario()
        while (
            self._actual() is not None
            and self._actual().tipo == "OP"
            and self._actual().lexema in ("*", "/")
        ):
            op = self._avanzar()
            der = self._parsear_primario()
            izq = nodos.Binaria(izq, op.lexema, der, op)
        return izq

    def _parsear_primario(self):
        token = self._actual()
        if token is None:
            raise self._fallo(None, "falta una expresion")
        if token.tipo == "NUM":
            self._avanzar()
            if "." in token.lexema:
                return nodos.Literal(float(token.lexema), token)
            return nodos.Literal(int(token.lexema), token)
        if token.tipo == "IDENT":
            self._avanzar()
            return nodos.Variable(token.lexema, token)
        if token.tipo == "OP" and token.lexema == "(":
            self._avanzar()
            expr = self._parsear_expr()
            cierre = self._actual()
            if cierre is None or cierre.tipo != "OP" or cierre.lexema != ")":
                raise self._fallo(cierre, "falta cerrar el parentesis")
            self._avanzar()
            return expr
        raise self._fallo(token, "se esperaba una expresion")


def parsear(texto: str) -> nodos.Programa:
    return _Parser(tokenizar(texto)).parsear_programa()
