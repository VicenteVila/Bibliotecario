"""Informes de saldo."""

from __future__ import annotations

from collections.abc import Sequence

from ledger.models import Asiento, Cuenta


def balance_after(cuenta: Cuenta, asientos: Sequence[Asiento]) -> int:
    total = cuenta.balance_cents
    for asiento in asientos:
        if asiento.status == "posted":
            total += asiento.amount_cents
    return total
