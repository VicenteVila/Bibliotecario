"""Cálculo de comisiones."""

from __future__ import annotations


def fee_cents(amount_cents: int, rate_bps: int) -> int:
    return round(amount_cents * rate_bps / 10000)
