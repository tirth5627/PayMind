"""Policy gate — enforces spend caps and validates purchase requests.

Step 1: Hard spend cap only.
Step 2: Full mandate-producing gate with Intent/Cart/Payment mandates.
"""

from audit.logger import log_event

# Hard per-session spend cap in paise (₹2,000)
DEFAULT_SESSION_CAP_PAISE = 200_000

# Category allow-list (all categories allowed for now)
ALLOWED_CATEGORIES = {"groceries", "snacks", "personal_care", "electronics"}

# Single-item price sanity limit in paise (₹1,500)
SINGLE_ITEM_PRICE_LIMIT = 150_000


class PolicyResult:
    """Result of a policy check."""

    def __init__(self, allowed: bool, reason: str, rule: str):
        self.allowed = allowed
        self.reason = reason
        self.rule = rule  # which rule triggered

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "rule": self.rule,
        }


def check_spend_cap(
    cart_total: int,
    session_spent: int = 0,
    session_cap: int = DEFAULT_SESSION_CAP_PAISE,
    mandate_ref: str | None = None,
) -> PolicyResult:
    """
    Check if the proposed cart total is within the session spend cap.

    Args:
        cart_total: Total amount of the current cart in paise
        session_spent: Amount already spent in this session in paise
        session_cap: Maximum allowed spend per session in paise
        mandate_ref: Optional mandate reference for audit trail

    Returns:
        PolicyResult with allowed/blocked status and reason
    """
    remaining = session_cap - session_spent
    new_total = session_spent + cart_total

    if new_total > session_cap:
        result = PolicyResult(
            allowed=False,
            reason=(
                f"Spend cap exceeded. Cart total: ₹{cart_total / 100:.2f}, "
                f"already spent: ₹{session_spent / 100:.2f}, "
                f"cap: ₹{session_cap / 100:.2f}, "
                f"remaining: ₹{remaining / 100:.2f}. "
                f"Explicit buyer approval required to proceed."
            ),
            rule="session_spend_cap",
        )
    else:
        result = PolicyResult(
            allowed=True,
            reason=(
                f"Within spend cap. Cart total: ₹{cart_total / 100:.2f}, "
                f"session total after purchase: ₹{new_total / 100:.2f}, "
                f"cap: ₹{session_cap / 100:.2f}."
            ),
            rule="session_spend_cap",
        )

    log_event(
        actor="gate",
        action="spend_cap_check",
        reason=result.reason,
        mandate_ref=mandate_ref,
        amount=cart_total,
        rule_outcome="allowed" if result.allowed else "blocked",
    )

    return result


def check_category(category: str, mandate_ref: str | None = None) -> PolicyResult:
    """Check if a product category is on the allow-list."""
    if category in ALLOWED_CATEGORIES:
        result = PolicyResult(
            allowed=True,
            reason=f"Category '{category}' is on the allow-list.",
            rule="category_allowlist",
        )
    else:
        result = PolicyResult(
            allowed=False,
            reason=f"Category '{category}' is NOT on the allow-list. Allowed: {ALLOWED_CATEGORIES}.",
            rule="category_allowlist",
        )

    log_event(
        actor="gate",
        action="category_check",
        reason=result.reason,
        mandate_ref=mandate_ref,
        rule_outcome="allowed" if result.allowed else "blocked",
    )

    return result


def check_single_item_price(
    price: int, product_name: str, mandate_ref: str | None = None
) -> PolicyResult:
    """Sanity check on individual item price."""
    if price > SINGLE_ITEM_PRICE_LIMIT:
        result = PolicyResult(
            allowed=False,
            reason=(
                f"Item '{product_name}' costs ₹{price / 100:.2f}, "
                f"which exceeds the single-item limit of ₹{SINGLE_ITEM_PRICE_LIMIT / 100:.2f}. "
                f"Explicit buyer approval required."
            ),
            rule="single_item_price_limit",
        )
    else:
        result = PolicyResult(
            allowed=True,
            reason=f"Item '{product_name}' at ₹{price / 100:.2f} is within single-item limit.",
            rule="single_item_price_limit",
        )

    log_event(
        actor="gate",
        action="item_price_check",
        reason=result.reason,
        mandate_ref=mandate_ref,
        amount=price,
        rule_outcome="allowed" if result.allowed else "blocked",
    )

    return result


def run_all_checks(
    cart_items: list[dict],
    cart_total: int,
    session_spent: int = 0,
    session_cap: int = DEFAULT_SESSION_CAP_PAISE,
    mandate_ref: str | None = None,
) -> list[PolicyResult]:
    """
    Run all policy checks against a cart. Returns a list of PolicyResults.
    Any blocked result means the purchase should not proceed without approval.
    """
    results = []

    # 1. Spend cap check
    results.append(
        check_spend_cap(cart_total, session_spent, session_cap, mandate_ref)
    )

    # 2. Category and price checks for each item
    for item in cart_items:
        results.append(
            check_category(item.get("category", "unknown"), mandate_ref)
        )
        results.append(
            check_single_item_price(
                item.get("price", 0) * item.get("quantity", 1),
                item.get("name", "unknown"),
                mandate_ref,
            )
        )

    return results
