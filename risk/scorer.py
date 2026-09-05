"""Risk Scorer — real-time payment compliance and anomaly scoring.

Computes a 0-100 risk score per session based on:
- Spend velocity (spending close to cap = high risk)
- Category risk profile (electronics > groceries)
- Session behaviour (blocked attempts, overrides)
- Cart composition (high-value single items)
"""

from typing import Optional
import time

# Category risk weights (higher = more scrutiny needed)
CATEGORY_RISK = {
    "electronics": 0.85,
    "personal_care": 0.30,
    "snacks": 0.10,
    "groceries": 0.05,
}

# Thresholds
SESSION_CAP_PAISE = 200_000  # ₹2,000


def compute_risk_score(
    session_spent: int,
    cart_total: int,
    cart_items: list[dict],
    blocked_attempts: int = 0,
    override_count: int = 0,
) -> dict:
    """
    Compute a composite risk score for a session.

    Returns a dict with:
      score: 0-100 (0 = safe, 100 = highest risk)
      level: "low" | "medium" | "high" | "critical"
      factors: list of contributing factors with individual scores
      recommendation: human-readable summary
    """
    factors = []
    score = 0.0

    # 1. Spend velocity risk (how close to cap)
    projected_total = session_spent + cart_total
    velocity_ratio = projected_total / SESSION_CAP_PAISE
    velocity_score = min(velocity_ratio * 60, 60)  # max 60 pts
    factors.append({
        "name": "Spend Velocity",
        "score": round(velocity_score, 1),
        "detail": f"₹{projected_total / 100:.0f} of ₹{SESSION_CAP_PAISE / 100:.0f} cap used ({velocity_ratio * 100:.1f}%)",
    })
    score += velocity_score

    # 2. Category risk
    if cart_items:
        category_scores = []
        for item in cart_items:
            cat = item.get("category", "unknown")
            cat_risk = CATEGORY_RISK.get(cat, 0.4)
            category_scores.append(cat_risk)
        avg_cat_risk = sum(category_scores) / len(category_scores)
        cat_score = avg_cat_risk * 20  # max 20 pts
        top_cat = max(cart_items, key=lambda x: CATEGORY_RISK.get(x.get("category", ""), 0.4))
        factors.append({
            "name": "Category Risk",
            "score": round(cat_score, 1),
            "detail": f"Highest risk category: {top_cat.get('category', 'unknown')}",
        })
        score += cat_score

    # 3. Override/blocked behaviour risk
    behaviour_score = min((blocked_attempts * 5 + override_count * 8), 20)  # max 20 pts
    if blocked_attempts > 0 or override_count > 0:
        factors.append({
            "name": "Behaviour Flags",
            "score": behaviour_score,
            "detail": f"{blocked_attempts} blocked attempt(s), {override_count} override(s)",
        })
        score += behaviour_score

    # Clamp to 0-100
    score = min(max(score, 0), 100)

    # Level classification
    if score < 25:
        level = "low"
        color = "#22c55e"
        recommendation = "Transaction appears routine. Standard audit logging active."
    elif score < 50:
        level = "medium"
        color = "#f59e0b"
        recommendation = "Elevated spend detected. Mandate verification recommended."
    elif score < 75:
        level = "high"
        color = "#f97316"
        recommendation = "High spend velocity or risky category. Human review advised."
    else:
        level = "critical"
        color = "#ef4444"
        recommendation = "Critical risk: multiple flags triggered. Block and escalate."

    return {
        "score": round(score, 1),
        "level": level,
        "color": color,
        "factors": factors,
        "recommendation": recommendation,
        "timestamp": time.time(),
        "inputs": {
            "session_spent": session_spent,
            "cart_total": cart_total,
            "projected_total": projected_total,
            "blocked_attempts": blocked_attempts,
            "override_count": override_count,
        },
    }


def get_category_breakdown(cart_items: list[dict]) -> list[dict]:
    """Return risk breakdown by category for visualization."""
    breakdown = {}
    for item in cart_items:
        cat = item.get("category", "unknown")
        if cat not in breakdown:
            breakdown[cat] = {
                "category": cat,
                "risk_weight": CATEGORY_RISK.get(cat, 0.4),
                "item_count": 0,
                "total_amount": 0,
            }
        breakdown[cat]["item_count"] += item.get("quantity", 1)
        breakdown[cat]["total_amount"] += item.get("price", 0) * item.get("quantity", 1)

    result = list(breakdown.values())
    result.sort(key=lambda x: -x["risk_weight"])
    return result
