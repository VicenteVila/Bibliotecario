"""Tests ocultos: motor (secuencias, terminales, ilegales, inmutabilidad)."""
import pytest
from approvalflow import IllegalTransition, StateMachine
from approvalflow.guards import GuardError


def test_secuencia_feliz_hasta_paid():
    sm = StateMachine()
    assert sm.apply("submit") == "submitted"
    assert sm.apply("approve", {"approver": "m1", "requester": "r1"}) == (
        "manager_approved"
    )
    assert sm.apply("approve") == "finance_approved"
    assert sm.apply("pay") == "paid"
    assert sm.state == "paid"


def test_flujo_completo_con_escalada():
    sm = StateMachine()
    sm.apply("submit")
    assert sm.apply("escalate", {"amount": 1000}) == "escalated"
    assert sm.apply("approve", {"approver": "f1", "requester": "r1"}) == (
        "finance_approved"
    )
    assert sm.apply("pay") == "paid"


def test_terminal_rejected_mensaje_exacto():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("reject", {"note": "x"})
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("submit")
    assert str(exc.value) == "terminal: rejected"
    assert sm.state == "rejected"


def test_terminal_paid_mensaje_exacto():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("approve", {"approver": "m1", "requester": "r1"})
    sm.apply("approve")
    sm.apply("pay")
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("pay")
    assert str(exc.value) == "terminal: paid"


def test_terminal_cancelled_bloquea_eventos():
    sm = StateMachine()
    sm.apply("cancel")
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("submit")
    assert str(exc.value) == "terminal: cancelled"


def test_illegal_mensaje_desde_draft():
    sm = StateMachine()
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("pay")
    assert str(exc.value) == "illegal: draft -pay-> ?"


def test_illegal_evento_vacio():
    sm = StateMachine()
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("")
    assert str(exc.value) == "illegal: draft --> ?"


def test_illegal_evento_repetido_desde_submitted():
    sm = StateMachine()
    sm.apply("submit")
    with pytest.raises(IllegalTransition) as exc:
        sm.apply("submit")
    assert str(exc.value) == "illegal: submitted -submit-> ?"


def test_estado_inmutable_tras_illegal():
    sm = StateMachine()
    sm.apply("submit")
    with pytest.raises(IllegalTransition):
        sm.apply("pay")
    assert sm.state == "submitted"


def test_estado_inmutable_tras_guard_error():
    sm = StateMachine()
    sm.apply("submit")
    with pytest.raises(GuardError):
        sm.apply("escalate")
    assert sm.state == "submitted"


def test_cancel_desde_submitted_no_tiene_guards():
    sm = StateMachine()
    sm.apply("submit")
    assert sm.apply("cancel") == "cancelled"


def test_cancel_desde_manager_approved():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("approve", {"approver": "m1", "requester": "r1"})
    assert sm.apply("cancel") == "cancelled"


def test_reject_desde_escalated_con_nota():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("escalate", {"amount": 5000})
    assert sm.apply("reject", {"note": "no aplica"}) == "rejected"


def test_reject_desde_manager_approved_con_nota():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("approve", {"approver": "m1", "requester": "r1"})
    assert sm.apply("reject", {"note": "política"}) == "rejected"


def test_typeerror_evento_no_str():
    sm = StateMachine()
    with pytest.raises(TypeError) as exc:
        sm.apply(42)
    assert str(exc.value) == "event must be str"


def test_typeerror_ctx_invalido():
    sm = StateMachine()
    with pytest.raises(TypeError) as exc:
        sm.apply("submit", ["no"])
    assert str(exc.value) == "ctx must be dict or None"


def test_typeerror_se_evalua_antes_que_terminal():
    sm = StateMachine()
    sm.apply("submit")
    sm.apply("reject", {"note": "x"})
    with pytest.raises(TypeError):
        sm.apply(123)


def test_maquinas_independientes():
    a = StateMachine()
    b = StateMachine()
    a.apply("submit")
    assert a.state == "submitted"
    assert b.state == "draft"


def test_state_es_readonly_no_metodo_setter():
    sm = StateMachine()
    with pytest.raises(AttributeError):
        sm.state = "paid"
