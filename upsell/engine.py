"""Upsell engine — keyword-overlap similarity for product recommendations.

No heavy ML dependencies — uses TF-IDF-like word overlap scoring between
cart item descriptions and candidate product descriptions. Good enough for
10 products and fast enough for real-time during checkout.
"""

import re
from collections import Counter
from catalog.db import search_products
from db.setup import get_connection
from audit.logger import log_event


# Common words to ignore when computing similarity
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "are", "was", "were",
    "be", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "can", "this", "that", "these", "those", "not", "no",
}


def _tokenize(text: str) -> list[str]:
    """Lowercase, split, remove stopwords and short tokens."""
    words = re.findall(r'[a-z]+', text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 2]


def _keyword_vector(texts: list[str]) -> Counter:
    """Build a keyword frequency counter from multiple text fields."""
    counter = Counter()
    for text in texts:
        counter.update(_tokenize(text))
    return counter


def _similarity_score(cart_keywords: Counter, product_keywords: Counter) -> float:
    """Compute overlap similarity between two keyword vectors."""
    if not cart_keywords or not product_keywords:
        return 0.0

    shared_keys = set(cart_keywords.keys()) & set(product_keywords.keys())
    if not shared_keys:
        return 0.0

    # Weighted overlap: sum of min frequencies for shared keywords
    overlap = sum(min(cart_keywords[k], product_keywords[k]) for k in shared_keys)
    total = sum(product_keywords.values())
    return overlap / max(total, 1)


def get_upsell_suggestions(
    cart_items: list[dict],
    top_n: int = 2,
    mandate_ref: str | None = None,
) -> list[dict]:
    """
    Given current cart items, suggest complementary products.

    Args:
        cart_items: List of dicts with at least 'product_id', 'name', 'description', 'category'
        top_n: Number of suggestions to return
        mandate_ref: Optional mandate reference for audit logging

    Returns:
        List of suggestion dicts: {product, relevance_score, reason}
    """
    # Build keyword profile from cart
    cart_texts = []
    cart_ids = set()
    for item in cart_items:
        cart_texts.extend([
            item.get("name", ""),
            item.get("description", ""),
            item.get("category", ""),
        ])
        cart_ids.add(item.get("product_id", ""))

    cart_keywords = _keyword_vector(cart_texts)

    # Get all products
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT id, name, price, stock, description, category FROM products WHERE stock > 0")
        all_products = [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

    # Score candidates
    candidates = []
    for product in all_products:
        if product["id"] in cart_ids:
            continue  # skip items already in cart

        prod_keywords = _keyword_vector([
            product["name"], product["description"], product["category"]
        ])
        score = _similarity_score(cart_keywords, prod_keywords)

        if score > 0:
            # Generate a human-readable reason
            shared = set(cart_keywords.keys()) & set(prod_keywords.keys())
            reason_words = sorted(shared, key=lambda w: -cart_keywords[w])[:3]
            reason = f"Related keywords: {', '.join(reason_words)}"

            candidates.append({
                "product": product,
                "relevance_score": round(score, 3),
                "reason": reason,
            })

    # Sort by score descending
    candidates.sort(key=lambda x: -x["relevance_score"])
    suggestions = candidates[:top_n]

    # Log
    if suggestions:
        names = ", ".join(s["product"]["name"] for s in suggestions)
        log_event(
            actor="orchestrator",
            action="upsell_suggestions_generated",
            reason=f"Suggested {len(suggestions)} upsell(s): {names}",
            mandate_ref=mandate_ref,
        )
    else:
        log_event(
            actor="orchestrator",
            action="upsell_no_suggestions",
            reason="No relevant upsell suggestions found for current cart",
            mandate_ref=mandate_ref,
        )

    return suggestions


# Session-level tracking for upsell metrics
class UpsellTracker:
    """Tracks upsell offer/acceptance rates per session."""

    def __init__(self):
        self.offered: int = 0
        self.accepted: int = 0

    def record_offer(self, count: int = 1):
        self.offered += count

    def record_acceptance(self, count: int = 1):
        self.accepted += count

    @property
    def acceptance_rate(self) -> float:
        if self.offered == 0:
            return 0.0
        return self.accepted / self.offered

    def to_dict(self) -> dict:
        return {
            "offered": self.offered,
            "accepted": self.accepted,
            "acceptance_rate": round(self.acceptance_rate * 100, 1),
            "acceptance_rate_display": f"{self.acceptance_rate * 100:.1f}%",
        }
