"""Guardas del workflow: cada guarda recibe el ctx y lanza GuardError."""
from __future__ import annotations


class GuardError(Exception):
    """El ctx no cumple la guarda de la transición."""


def note_required(ctx: dict) -> None:
    """Exige un note no vacío."""
    note = ctx.get("note")
    if not isinstance(note, str) or note == "":
        raise GuardError("note required")


def amount_ge_1000(ctx: dict) -> None:
    """Exige un amount numérico (no bool) >= 1000."""
    amount = ctx.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise GuardError("amount required")
    if amount < 1000:
        raise GuardError("amount below 1000")


def approver_not_requester(ctx: dict) -> None:
    """Exige approver y requester distintos y presentes."""
    approver = ctx.get("approver")
    requester = ctx.get("requester")
    if approver is None or requester is None:
        raise GuardError("approver and requester required")
    if approver == requester:
        raise GuardError("approver equals requester")


GUARDS = {
    "note_required": note_required,
    "amount_ge_1000": amount_ge_1000,
    "approver_not_requester": approver_not_requester,
}
