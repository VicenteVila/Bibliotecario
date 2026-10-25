"""Servicio de nómina pendiente de completar."""

from __future__ import annotations

from nomina.models import Nomina, Resultado


def procesar(nomina: Nomina) -> Resultado:
    bruto = (
        nomina.horas * nomina.tarifa_cents
        + nomina.horas_extra * nomina.tarifa_cents
    )
    return Resultado(bruto=bruto, impuesto=0, neto=bruto)
