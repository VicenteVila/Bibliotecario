"""Servicio de nómina."""

from __future__ import annotations

from nomina.models import Nomina, Resultado
from nomina.rules import bruto, impuesto, neto


def procesar(nomina: Nomina) -> Resultado:
    bruto_cents = bruto(nomina)
    impuesto_cents = impuesto(bruto_cents, nomina.tasa_pct)
    return Resultado(
        bruto=bruto_cents,
        impuesto=impuesto_cents,
        neto=neto(bruto_cents, impuesto_cents),
    )
