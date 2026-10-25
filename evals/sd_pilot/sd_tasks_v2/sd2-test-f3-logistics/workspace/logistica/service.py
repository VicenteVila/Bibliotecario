"""Fachada de cotización pendiente de implementar."""

from __future__ import annotations

from logistica.models import Envio, Resultado


class Cotizador:
    def __init__(self, envio: Envio) -> None:
        self._envio = envio

    def base(self) -> int:
        raise NotImplementedError

    def recargos(self) -> int:
        raise NotImplementedError

    def total(self) -> int:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
