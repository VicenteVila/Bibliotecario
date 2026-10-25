"""Modelos del libro de movimientos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cuenta:
    cuenta_id: str
    balance_cents: int
    overdraft_limit_cents: int


@dataclass(frozen=True)
class Asiento:
    asiento_id: str
    cuenta_id: str
    amount_cents: int
    status: str = "posted"
