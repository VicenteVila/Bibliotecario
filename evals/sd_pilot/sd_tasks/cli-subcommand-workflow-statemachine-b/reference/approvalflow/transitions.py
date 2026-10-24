"""Tabla legal de transiciones del workflow.

Cada entrada: (estado, evento) -> (destino, guard_id | None).
"""
from __future__ import annotations

TRANSITIONS: dict[tuple[str, str], tuple[str, str | None]] = {
    ("draft", "submit"): ("submitted", None),
    ("draft", "cancel"): ("cancelled", None),
    ("submitted", "approve"): ("manager_approved", "approver_not_requester"),
    ("submitted", "reject"): ("rejected", "note_required"),
    ("submitted", "escalate"): ("escalated", "amount_ge_1000"),
    ("submitted", "cancel"): ("cancelled", None),
    ("escalated", "approve"): ("finance_approved", "approver_not_requester"),
    ("escalated", "reject"): ("rejected", "note_required"),
    ("manager_approved", "approve"): ("finance_approved", None),
    ("manager_approved", "reject"): ("rejected", "note_required"),
    ("manager_approved", "cancel"): ("cancelled", None),
    ("finance_approved", "pay"): ("paid", None),
}
