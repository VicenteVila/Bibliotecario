"""Tests ocultos: guardas (mensajes exactos y bordes)."""
import pytest
from approvalflow import StateMachine
from approvalflow.guards import GuardError


def _en_submitted() -> StateMachine:
    sm = StateMachine()
    sm.apply("submit")
    return sm


def test_escalate_sin_ctx_pide_amount():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("escalate")
    assert str(exc.value) == "amount required"


def test_escalate_amount_no_numerico():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("escalate", {"amount": "1000"})
    assert str(exc.value) == "amount required"


def test_escalate_amount_bool_no_cuenta_como_numero():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("escalate", {"amount": True})
    assert str(exc.value) == "amount required"


def test_escalate_amount_bajo_threshold():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("escalate", {"amount": 999})
    assert str(exc.value) == "amount below 1000"


def test_escalate_amount_bajo_threshold_flotante():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("escalate", {"amount": 999.99})
    assert str(exc.value) == "amount below 1000"


def test_escalate_amount_en_borde_pasa():
    sm = _en_submitted()
    assert sm.apply("escalate", {"amount": 1000}) == "escalated"


def test_reject_sin_note():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("reject")
    assert str(exc.value) == "note required"


def test_reject_note_vacia():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("reject", {"note": ""})
    assert str(exc.value) == "note required"


def test_reject_note_no_str():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("reject", {"note": 3})
    assert str(exc.value) == "note required"


def test_approve_sin_ctx_requiere_approver_y_requester():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("approve")
    assert str(exc.value) == "approver and requester required"


def test_approve_approver_igual_a_requester():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("approve", {"approver": "ana", "requester": "ana"})
    assert str(exc.value) == "approver equals requester"


def test_approve_requester_faltante():
    sm = _en_submitted()
    with pytest.raises(GuardError) as exc:
        sm.apply("approve", {"approver": "m1"})
    assert str(exc.value) == "approver and requester required"


def test_approve_desde_escalated_tambien_valida_guards():
    sm = _en_submitted()
    sm.apply("escalate", {"amount": 2500})
    with pytest.raises(GuardError) as exc:
        sm.apply("approve", {"approver": "x", "requester": "x"})
    assert str(exc.value) == "approver equals requester"
    assert sm.state == "escalated"


def test_approve_desde_manager_approved_no_tiene_guards():
    sm = _en_submitted()
    sm.apply("approve", {"approver": "m1", "requester": "r1"})
    assert sm.apply("approve") == "finance_approved"


def test_ctx_extra_se_ignora():
    sm = _en_submitted()
    assert sm.apply("escalate", {"amount": 1000, "extra": True}) == "escalated"
