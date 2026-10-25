"""Servicio de logística pendiente de completar."""

from __future__ import annotations

from logistica.models import Envio, Resultado


def procesar(envio: Envio) -> Resultado:
    base = (
        500
        + envio.peso_kg * 20
        + envio.volumen_l * 2
        + envio.distancia_km * 10
    )
    return Resultado(base=base, recargos=0, total=base)
