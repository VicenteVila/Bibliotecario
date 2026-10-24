"""Tests ocultos del informe de saldo."""

from ledger.models import Asiento, Cuenta
from ledger.reports import balance_after


def test_revertidos_no_cuentan():
    cuenta = Cuenta("A", 100, 500)
    asientos = [
        Asiento("p", "A", 50),
        Asiento("r", "A", -30, status="reversed"),
    ]
    assert balance_after(cuenta, asientos) == 150


def test_pendientes_no_cuentan():
    cuenta = Cuenta("A", 100, 500)
    asientos = [
        Asiento("p", "A", 50),
        Asiento("q", "A", -70, status="pending"),
    ]
    assert balance_after(cuenta, asientos) == 150


def test_todo_revertido_devuelve_saldo_base():
    cuenta = Cuenta("A", 100, 500)
    asientos = [
        Asiento("r1", "A", 50, status="reversed"),
        Asiento("r2", "A", -30, status="reversed"),
    ]
    assert balance_after(cuenta, asientos) == 100


def test_solo_posted_suma():
    cuenta = Cuenta("A", 0, 500)
    asientos = [
        Asiento("p1", "A", 50),
        Asiento("p2", "A", -20),
        Asiento("q", "A", 999, status="pending"),
    ]
    assert balance_after(cuenta, asientos) == 30
