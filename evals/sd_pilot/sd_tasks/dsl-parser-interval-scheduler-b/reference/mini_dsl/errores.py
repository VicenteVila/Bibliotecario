"""Errores del mini-DSL."""

from __future__ import annotations


class ErrorDeSintaxis(Exception):
    """Error léxico, sintáctico o semántico del contrato del DSL."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
