"""Estados del workflow de aprobaciones."""

INITIAL = "draft"

STATES = frozenset(
    {
        "draft",
        "submitted",
        "escalated",
        "manager_approved",
        "finance_approved",
        "rejected",
        "paid",
        "cancelled",
    }
)

TERMINALS = frozenset({"rejected", "paid", "cancelled"})
