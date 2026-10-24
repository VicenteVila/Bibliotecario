"""Tests públicos del informe de saldo."""

from ledger.models import Asiento, Cuenta
from ledger.reports import balance_after


def test_informe_ignora_revertidos():
    cuenta = Cuenta("A", 0, 1000)
    asientos = [
        Asiento("p", "A", 100),
        Asiento("r", "A", -30, status="reversed"),
    ]
    assert balance_after(cuenta, asientos) == 100


def test_informe_ignora_pendientes():
    cuenta = Cuenta("A", 0, 1000)
    asientos = [
        Asiento("p", "A", 100),
        Asiento("q", "A", -50, status="pending"),
    ]
    assert balance_after(cuenta, asientos) == 100


def test_informe_suma_posted():
    cuenta = Cuenta("A", 100, 1000)
    asientos = [Asiento("p", "A", 50), Asiento("q", "A", -20)]
    assert balance_after(cuenta, asientos) == 130
