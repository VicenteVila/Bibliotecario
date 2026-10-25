"""Servicio de logística."""

from __future__ import annotations

from logistica.models import Envio, Resultado
from logistica.rules import base, recargos, total


def procesar(envio: Envio) -> Resultado:
    base_cents = base(envio)
    recargos_cents = recargos(envio, base_cents)
    return Resultado(
        base=base_cents,
        recargos=recargos_cents,
        total=total(base_cents, recargos_cents),
    )
