"""Fachada de nómina."""

from __future__ import annotations

from nomina.models import Nomina, Resultado
from nomina.rules import bruto, impuesto, neto


class CalculoNomina:
    def __init__(self, nomina: Nomina) -> None:
        self._nomina = nomina

    def bruto(self) -> int:
        return bruto(self._nomina)

    def impuesto(self) -> int:
        return impuesto(self.bruto(), self._nomina.tasa_pct)

    def neto(self) -> int:
        return neto(self.bruto(), self.impuesto())

    def procesar(self) -> Resultado:
        return Resultado(
            bruto=self.bruto(),
            impuesto=self.impuesto(),
            neto=self.neto(),
        )
