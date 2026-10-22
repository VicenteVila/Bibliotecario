"""Workflow de aprobaciones: estados, transiciones, guardas y motor."""
from approvalflow.guards import GuardError
from approvalflow.machine import IllegalTransition, StateMachine
from approvalflow.states import INITIAL, STATES, TERMINALS

__all__ = [
    "INITIAL",
    "STATES",
    "TERMINALS",
    "GuardError",
    "IllegalTransition",
    "StateMachine",
]
