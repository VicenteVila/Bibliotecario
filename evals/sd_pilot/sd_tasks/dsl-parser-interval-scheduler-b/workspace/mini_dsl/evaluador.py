"""Evaluador preliminar: aritmética y let; errores informales."""

from __future__ import annotations

from mini_dsl import nodos
from mini_dsl.errores import ErrorDeSintaxis


def evaluar_programa(programa: nodos.Programa) -> list:
    entorno: dict[str, object] = {}
    resultados: list = []
    for sentencia in programa.sentencias:
        resultados.append(_evaluar_sentencia(sentencia, entorno))
    return resultados


def _evaluar_sentencia(sentencia, entorno: dict) -> object:
    if isinstance(sentencia, nodos.Definicion):
        if sentencia.nombre in entorno:
            raise ErrorDeSintaxis(
                f"la variable {sentencia.nombre} ya esta definida"
            )
        entorno[sentencia.nombre] = _evaluar(sentencia.expr, entorno)
        return None
    return _evaluar(sentencia.expr, entorno)


def _evaluar(expr, entorno: dict) -> object:
    if isinstance(expr, nodos.Literal):
        return expr.valor
    if isinstance(expr, nodos.Variable):
        if expr.nombre not in entorno:
            raise ErrorDeSintaxis(f"variable desconocida: {expr.nombre}")
        return entorno[expr.nombre]
    if isinstance(expr, nodos.Binaria):
        izq = _evaluar(expr.izq, entorno)
        der = _evaluar(expr.der, entorno)
        if expr.op == "+":
            return izq + der
        if expr.op == "-":
            return izq - der
        if expr.op == "*":
            return izq * der
        return izq / der
    raise ErrorDeSintaxis("expresion no soportada")
