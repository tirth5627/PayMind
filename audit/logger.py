"""Audit logger — single entry point for all modules to write audit events."""

from typing import Optional
from audit.db import insert_event


def log_event(
    actor: str,
    action: str,
    reason: str,
    mandate_ref: Optional[str] = None,
    amount: Optional[int] = None,
    rule_outcome: str = "n/a",
) -> int:
    """
    Log an auditable event. Every module in the system should call this.

    Args:
        actor: Who performed the action (buyer/orchestrator/catalog/gate/razorpay)
        action: What happened (e.g. "search_products", "create_order", "spend_cap_check")
        reason: Human-readable explanation of why this happened
        mandate_ref: Optional reference linking to a mandate chain
        amount: Optional amount in paise
        rule_outcome: "allowed", "blocked", or "n/a"

    Returns:
        The audit log row ID.
    """
    return insert_event(
        actor=actor,
        action=action,
        reason=reason,
        mandate_ref=mandate_ref,
        amount=amount,
        rule_outcome=rule_outcome,
    )
