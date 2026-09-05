"""Campaign Engine — Dynamic pricing rules and tracking.

Evaluates cart contents and user persona to apply dynamic discounts.
This demonstrates the "Campaign orchestrator" stretch goal.
"""
from typing import Optional
from audit.logger import log_event

# Mock campaigns
CAMPAIGNS = [
    {
        "id": "camp_ai_early_adopter",
        "name": "AI Early Adopter Bonus",
        "description": "10% off for all AI buyers to encourage automated commerce.",
        "condition": lambda buyer_id, cart_total, item_count: buyer_id.startswith("ai_"),
        "discount_pct": 10,
    },
    {
        "id": "camp_bulk_buyer",
        "name": "Bulk Buyer Discount",
        "description": "₹150 off when buying 4 or more items.",
        "condition": lambda buyer_id, cart_total, item_count: item_count >= 4,
        "discount_flat": 15000, # 150 INR in paise
    }
]

def evaluate_campaigns(buyer_id: str, cart_total: int, item_count: int, mandate_ref: Optional[str] = None) -> dict:
    """
    Evaluate available campaigns and return the best discount to apply.
    """
    best_discount = 0
    best_campaign = None
    
    for camp in CAMPAIGNS:
        if camp["condition"](buyer_id, cart_total, item_count):
            discount = 0
            if "discount_pct" in camp:
                discount = int(cart_total * (camp["discount_pct"] / 100))
            elif "discount_flat" in camp:
                discount = camp["discount_flat"]
                
            if discount > best_discount:
                best_discount = discount
                best_campaign = camp

    # Cap discount to cart total
    best_discount = min(best_discount, cart_total)
    
    if best_campaign:
        log_event(
            actor="orchestrator",
            action="campaign_applied",
            reason=f"Applied '{best_campaign['name']}' saving ₹{best_discount / 100:.2f}",
            mandate_ref=mandate_ref,
            amount=best_discount,
            rule_outcome="allowed"
        )
        return {
            "campaign_id": best_campaign["id"],
            "campaign_name": best_campaign["name"],
            "discount_amount": best_discount,
            "original_total": cart_total,
            "final_total": cart_total - best_discount,
            "message": f"🎉 {best_campaign['name']} applied! You saved ₹{best_discount / 100:.2f}."
        }
    
    return {
        "campaign_id": None,
        "discount_amount": 0,
        "original_total": cart_total,
        "final_total": cart_total
    }
