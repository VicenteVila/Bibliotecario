"""Reversión de asientos."""

from __future__ import annotations

from collections.abc import Sequence

from ledger.models import Asiento, Cuenta


def reverse_entry(asiento: Asiento, motivo: str) -> Asiento:
    if asiento.status != "posted":
        raise ValueError("solo se revierten asientos posted")
    if not motivo:
        raise ValueError("motivo requerido")
    return Asiento(
        asiento_id=f"rev-{asiento.asiento_id}",
        cuenta_id=asiento.cuenta_id,
        amount_cents=-asiento.amount_cents,
        status="posted",
    )


def apply_reversal(
    cuenta: Cuenta,
    asientos: Sequence[Asiento],
    asiento_id: str,
    motivo: str,
) -> tuple[Asiento, ...]:
    for asiento in asientos:
        if asiento.asiento_id == asiento_id:
            if any(
                a.asiento_id == f"rev-{asiento_id}" for a in asientos
            ):
                raise ValueError("asiento ya revertido")
            return tuple(asientos) + (reverse_entry(asiento, motivo),)
    raise ValueError(f"asiento no encontrado: {asiento_id}")
