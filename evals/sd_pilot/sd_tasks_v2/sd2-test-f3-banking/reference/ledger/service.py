"""Fachada del libro."""

from __future__ import annotations

from collections.abc import Iterable

from ledger.models import Asiento, Cuenta
from ledger.posting import balance_cents, post
from ledger.reports import balance_after


class Ledger:
    def __init__(
        self, cuenta: Cuenta, asientos: Iterable[Asiento]
    ) -> None:
        self._cuenta = cuenta
        self._asientos = list(asientos)

    def saldo(self) -> int:
        return balance_cents(self._cuenta, self._asientos)

    def registrar(self, asiento: Asiento) -> None:
        self._asientos = list(
            post(self._cuenta, self._asientos, asiento)
        )

    def informe(self) -> int:
        return balance_after(self._cuenta, self._asientos)

    def asientos_actuales(self) -> tuple[Asiento, ...]:
        return tuple(self._asientos)
