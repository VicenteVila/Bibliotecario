"""Nodos del AST del mini-DSL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mini_dsl.tokens import Token


@dataclass(frozen=True)
class Programa:
    sentencias: tuple


@dataclass(frozen=True)
class Definicion:
    nombre: str
    expr: Any
    token: Token


@dataclass(frozen=True)
class Expresion:
    expr: Any


@dataclass(frozen=True)
class Literal:
    valor: Any
    token: Token


@dataclass(frozen=True)
class Variable:
    nombre: str
    token: Token


@dataclass(frozen=True)
class Binaria:
    izq: Any
    op: str
    der: Any
    token: Token


@dataclass(frozen=True)
class Si:
    condicion: Any
    rama_si: Any
    rama_no: Any
    token: Token
