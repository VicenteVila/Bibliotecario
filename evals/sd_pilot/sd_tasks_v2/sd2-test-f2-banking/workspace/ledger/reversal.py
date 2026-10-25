"""Reversión de asientos."""

from __future__ import annotations

from collections.abc import Sequence

from ledger.models import Asiento, Cuenta


def reverse_entry(asiento: Asiento, motivo: str) -> Asiento:
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
            return tuple(asientos) + (reverse_entry(asiento, motivo),)
    raise ValueError(f"asiento no encontrado: {asiento_id}")
