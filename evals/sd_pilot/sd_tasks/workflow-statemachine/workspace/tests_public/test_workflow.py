"""Tests públicos: uso básico del motor del workflow."""
import pytest
from approvalflow import GuardError, IllegalTransition, StateMachine


def test_estado_inicial_es_draft():
    assert StateMachine().state == "draft"


def test_submit_avanza_a_submitted():
    sm = StateMachine()
    assert sm.apply("submit") == "submitted"
    assert sm.state == "submitted"


def test_evento_ilegal_lanza_illegal_transition():
    sm = StateMachine()
    with pytest.raises(IllegalTransition):
        sm.apply("pay")


def test_reject_desde_submitted_exige_nota():
    sm = StateMachine()
    sm.apply("submit")
    with pytest.raises(GuardError):
        sm.apply("reject")
    assert sm.state == "submitted"


def test_reject_con_nota_llega_a_rejected():
    sm = StateMachine()
    sm.apply("submit")
    assert sm.apply("reject", {"note": "sin presupuesto"}) == "rejected"
