"""Parser del mini-DSL con mensajes de error exactos y límite de profundidad."""

from __future__ import annotations

from mini_dsl import nodos
from mini_dsl.errores import ErrorDeSintaxis
from mini_dsl.lexer import tokenizar
from mini_dsl.tokens import Token

PROFUNDIDAD_MAXIMA = 32


class _Parser:
    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._i = 0
        self._profundidad = 0

    def _actual(self) -> Token | None:
        if self._i < len(self._tokens):
            return self._tokens[self._i]
        return None

    def _avanzar(self) -> Token:
        token = self._tokens[self._i]
        self._i += 1
        return token

    def _pos_fin(self) -> tuple[int, int]:
        if not self._tokens:
            return 1, 1
        ultimo = self._tokens[-1]
        if ultimo.tipo == "NL":
            return ultimo.linea + 1, 1
        return ultimo.linea, ultimo.columna + len(ultimo.lexema)

    def _error_en(self, token: Token, motivo: str) -> ErrorDeSintaxis:
        return ErrorDeSintaxis(
            f"error(L{token.linea},C{token.columna}): {motivo}"
        )

    def _error_eof(self, motivo: str) -> ErrorDeSintaxis:
        linea, columna = self._pos_fin()
        return ErrorDeSintaxis(f"error(L{linea},C{columna}): {motivo}")

    def parsear_programa(self) -> nodos.Programa:
        sentencias: list = []
        while True:
            while (
                self._actual() is not None
                and self._actual().tipo == "NL"
            ):
                self._avanzar()
            if self._actual() is None:
                break
            sentencias.append(self._parsear_sentencia())
            actual = self._actual()
            if actual is None:
                break
            if actual.tipo == "NL":
                self._avanzar()
                continue
            raise self._error_en(
                actual, f"se esperaba fin de línea pero llegó {actual.lexema!r}"
            )
        return nodos.Programa(sentencias=tuple(sentencias))

    def _parsear_sentencia(self):
        token = self._actual()
        if token is not None and token.tipo == "PALABRA" and token.lexema == "let":
            self._avanzar()
            nombre = self._actual()
            if nombre is None:
                raise self._error_eof(
                    "se esperaba un identificador pero llegó fin de entrada"
                )
            if nombre.tipo == "PALABRA":
                raise self._error_en(
                    nombre, f"identificador reservado: {nombre.lexema}"
                )
            if nombre.tipo != "IDENT":
                raise self._error_en(
                    nombre,
                    f"se esperaba un identificador pero llegó {nombre.lexema!r}",
                )
            self._avanzar()
            igual = self._actual()
            if igual is None:
                raise self._error_eof(
                    "se esperaba el operador '=' pero llegó fin de entrada"
                )
            if igual.tipo != "OP" or igual.lexema != "=":
                raise self._error_en(
                    igual,
                    f"se esperaba el operador '=' pero llegó {igual.lexema!r}",
                )
            self._avanzar()
            expr = self._parsear_expr()
            return nodos.Definicion(nombre.lexema, expr, nombre)
        return nodos.Expresion(self._parsear_expr())

    def _parsear_expr(self):
        token = self._actual()
        if token is not None and token.tipo == "PALABRA" and token.lexema == "si":
            self._abrir(token)
            self._avanzar()
            condicion = self._parsear_expr()
            entonces = self._actual()
            if entonces is None:
                raise self._error_eof(
                    "se esperaba una palabra clave 'entonces' pero llegó "
                    "fin de entrada"
                )
            if entonces.tipo != "PALABRA" or entonces.lexema != "entonces":
                raise self._error_en(
                    entonces,
                    "se esperaba una palabra clave 'entonces' pero llegó "
                    f"{entonces.lexema!r}",
                )
            self._avanzar()
            rama_si = self._parsear_expr()
            sino = self._actual()
            if sino is None:
                raise self._error_eof(
                    "se esperaba una palabra clave 'sino' pero llegó "
                    "fin de entrada"
                )
            if sino.tipo != "PALABRA" or sino.lexema != "sino":
                raise self._error_en(
                    sino,
                    "se esperaba una palabra clave 'sino' pero llegó "
                    f"{sino.lexema!r}",
                )
            self._avanzar()
            rama_no = self._parsear_expr()
            self._cerrar()
            return nodos.Si(condicion, rama_si, rama_no, token)
        return self._parsear_comp()

    def _abrir(self, token: Token) -> None:
        self._profundidad += 1
        if self._profundidad > PROFUNDIDAD_MAXIMA:
            raise self._error_en(
                token,
                f"profundidad maxima excedida (maxima: {PROFUNDIDAD_MAXIMA})",
            )

    def _cerrar(self) -> None:
        self._profundidad -= 1

    def _parsear_comp(self):
        izq = self._parsear_suma()
        actual = self._actual()
        if (
            actual is not None
            and actual.tipo == "OP"
            and actual.lexema in ("==", "!=", "<", "<=", ">", ">=")
        ):
            self._avanzar()
            der = self._parsear_suma()
            return nodos.Binaria(izq, actual.lexema, der, actual)
        return izq

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
            raise self._error_eof("se esperaba un valor pero llegó fin de entrada")
        if token.tipo == "NUM":
            self._avanzar()
            if "." in token.lexema:
                return nodos.Literal(float(token.lexema), token)
            return nodos.Literal(int(token.lexema), token)
        if token.tipo == "CADENA":
            self._avanzar()
            valor = token.lexema.replace('\\"', '"').replace("\\\\", "\\")
            return nodos.Literal(valor, token)
        if token.tipo == "PALABRA" and token.lexema in ("verdadero", "falso"):
            self._avanzar()
            return nodos.Literal(token.lexema == "verdadero", token)
        if token.tipo == "IDENT":
            self._avanzar()
            return nodos.Variable(token.lexema, token)
        if token.tipo == "OP" and token.lexema == "(":
            self._abrir(token)
            self._avanzar()
            expr = self._parsear_expr()
            cierre = self._actual()
            if cierre is None:
                raise self._error_eof(
                    "se esperaba ) pero llegó fin de entrada"
                )
            if cierre.tipo != "OP" or cierre.lexema != ")":
                raise self._error_en(
                    cierre, f"se esperaba ) pero llegó {cierre.lexema!r}"
                )
            self._avanzar()
            self._cerrar()
            return expr
        if token.tipo == "NL":
            raise self._error_en(
                token, f"se esperaba un valor pero llegó {token.lexema!r}"
            )
        raise self._error_en(token, f"token inesperado: {token.lexema!r}")


def parsear(texto: str) -> nodos.Programa:
    return _Parser(tokenizar(texto)).parsear_programa()
