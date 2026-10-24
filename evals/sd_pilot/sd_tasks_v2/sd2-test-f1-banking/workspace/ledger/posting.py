"""Registro de asientos y saldo."""

from __future__ import annotations

from collections.abc import Sequence

from ledger.models import Asiento, Cuenta


def balance_cents(cuenta: Cuenta, asientos: Sequence[Asiento]) -> int:
    total = cuenta.balance_cents
    for asiento in asientos:
        if asiento.status == "posted":
            total += asiento.amount_cents
    return total


def post(
    cuenta: Cuenta, asientos: Sequence[Asiento], nuevo: Asiento
) -> tuple[Asiento, ...]:
    for asiento in asientos:
        if asiento.asiento_id == nuevo.asiento_id:
            raise ValueError(f"asiento duplicado: {nuevo.asiento_id}")
    nuevo_balance = balance_cents(cuenta, asientos) + nuevo.amount_cents
    if nuevo_balance <= -cuenta.overdraft_limit_cents:
        raise ValueError("limite de descubierto excedido")
    return tuple(asientos) + (nuevo,)
