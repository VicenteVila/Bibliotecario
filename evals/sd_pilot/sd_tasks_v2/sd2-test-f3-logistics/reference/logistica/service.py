"""Fachada de cotización logística."""

from __future__ import annotations

from logistica.models import Envio, Resultado
from logistica.rules import base, recargos, total


class Cotizador:
    def __init__(self, envio: Envio) -> None:
        self._envio = envio

    def base(self) -> int:
        return base(self._envio)

    def recargos(self) -> int:
        return recargos(self._envio, self.base())

    def total(self) -> int:
        return total(self.base(), self.recargos())

    def procesar(self) -> Resultado:
        return Resultado(
            base=self.base(),
            recargos=self.recargos(),
            total=self.total(),
        )
