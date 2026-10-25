"""Servicio de reservas."""

from __future__ import annotations

from collections.abc import Sequence

from reservas.models import Reserva, Resultado
from reservas.rules import alerta, caducadas, disponible


def procesar(
    capacidad: int, reservas: Sequence[Reserva], now: int
) -> Resultado:
    disp = disponible(capacidad, reservas, now)
    return Resultado(
        disponible=disp,
        caducadas=caducadas(reservas, now),
        alerta=alerta(disp),
    )
