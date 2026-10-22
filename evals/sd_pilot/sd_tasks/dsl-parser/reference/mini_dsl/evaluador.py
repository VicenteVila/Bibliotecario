"""Evaluador del mini-DSL: semántica y errores del contrato."""

from __future__ import annotations

from mini_dsl import nodos
from mini_dsl.errores import ErrorDeSintaxis


def _error_en(token, motivo: str) -> ErrorDeSintaxis:
    return ErrorDeSintaxis(f"error(L{token.linea},C{token.columna}): {motivo}")


def _tipo(valor: object) -> str:
    if isinstance(valor, bool):
        return "booleano"
    if isinstance(valor, (int, float)):
        return "numero"
    if isinstance(valor, str):
        return "cadena"
    raise ErrorDeSintaxis("valor interno sin tipo")


def evaluar_programa(programa: nodos.Programa) -> list:
    entorno: dict[str, object] = {}
    resultados: list = []
    for sentencia in programa.sentencias:
        resultados.append(_evaluar_sentencia(sentencia, entorno))
    return resultados


def _evaluar_sentencia(sentencia, entorno: dict) -> object:
    if isinstance(sentencia, nodos.Definicion):
        if sentencia.nombre in entorno:
            raise _error_en(
                sentencia.token, f"variable redefinida: {sentencia.nombre}"
            )
        entorno[sentencia.nombre] = _evaluar(sentencia.expr, entorno)
        return None
    return _evaluar(sentencia.expr, entorno)


def _evaluar(expr, entorno: dict) -> object:
    if isinstance(expr, nodos.Literal):
        return expr.valor
    if isinstance(expr, nodos.Variable):
        if expr.nombre not in entorno:
            raise _error_en(
                expr.token, f"variable no definida: {expr.nombre}"
            )
        return entorno[expr.nombre]
    if isinstance(expr, nodos.Si):
        cond = _evaluar(expr.condicion, entorno)
        if not isinstance(cond, bool):
            raise _error_en(
                expr.token,
                "la condicion de 'si' debe ser booleana, es "
                f"{_tipo(cond)}",
            )
        return _evaluar(expr.rama_si if cond else expr.rama_no, entorno)
    if isinstance(expr, nodos.Binaria):
        izq = _evaluar(expr.izq, entorno)
        der = _evaluar(expr.der, entorno)
        return _evaluar_binaria(izq, expr.op, der, expr.token)
    raise ErrorDeSintaxis("expresion interna desconocida")


def _evaluar_binaria(izq: object, op: str, der: object, token) -> object:
    t_izq = _tipo(izq)
    t_der = _tipo(der)
    if t_izq != t_der:
        raise _error_en(
            token,
            f"tipo invalido para operador {op}: {t_izq} {op} {t_der}",
        )
    if op == "+":
        if t_izq == "booleano":
            raise _error_en(
                token,
                f"tipo invalido para operador {op}: {t_izq} {op} {t_der}",
            )
        return izq + der  # type: ignore[operator]
    if op == "-":
        if t_izq != "numero":
            raise _error_en(
                token,
                f"tipo invalido para operador {op}: {t_izq} {op} {t_der}",
            )
        return izq - der  # type: ignore[operator]
    if op == "*":
        if t_izq != "numero":
            raise _error_en(
                token,
                f"tipo invalido para operador {op}: {t_izq} {op} {t_der}",
            )
        return izq * der  # type: ignore[operator]
    if op == "/":
        if t_izq != "numero":
            raise _error_en(
                token,
                f"tipo invalido para operador {op}: {t_izq} {op} {t_der}",
            )
        if der == 0:
            raise _error_en(token, "division entre cero")
        return izq / der  # type: ignore[operator]
    if op == "==":
        return izq == der  # type: ignore[operator]
    if op == "!=":
        return izq != der  # type: ignore[operator]
    if op == "<":
        return izq < der  # type: ignore[operator]
    if op == "<=":
        return izq <= der  # type: ignore[operator]
    if op == ">":
        return izq > der  # type: ignore[operator]
    if op == ">=":
        return izq >= der  # type: ignore[operator]
    raise ErrorDeSintaxis(f"operador interno desconocido: {op}")
