"""Fachada del libro pendiente de implementar."""

from __future__ import annotations

from collections.abc import Iterable

from ledger.models import Asiento, Cuenta


class Ledger:
    def __init__(
        self, cuenta: Cuenta, asientos: Iterable[Asiento]
    ) -> None:
        self._cuenta = cuenta
        self._asientos = list(asientos)

    def saldo(self) -> int:
        raise NotImplementedError

    def registrar(self, asiento: Asiento) -> None:
        raise NotImplementedError

    def informe(self) -> int:
        raise NotImplementedError

    def asientos_actuales(self) -> tuple[Asiento, ...]:
        raise NotImplementedError
