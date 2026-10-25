"""Fachada de nómina pendiente de implementar."""

from __future__ import annotations

from nomina.models import Nomina, Resultado


class CalculoNomina:
    def __init__(self, nomina: Nomina) -> None:
        self._nomina = nomina

    def bruto(self) -> int:
        raise NotImplementedError

    def impuesto(self) -> int:
        raise NotImplementedError

    def neto(self) -> int:
        raise NotImplementedError

    def procesar(self) -> Resultado:
        raise NotImplementedError
