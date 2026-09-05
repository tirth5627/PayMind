"""x402 Payment Protocol — HTTP 402-based machine payment flow.

Implements Coinbase's x402 protocol for instant stablecoin/test payments:
  - Server returns HTTP 402 with payment requirements
  - Client attaches payment proof in X-PAYMENT header
  - Server verifies and returns resource with X-PAYMENT-RESPONSE

In our implementation we use Razorpay test-mode as the "payment rail"
instead of stablecoins, making it fully functional without real crypto.

Reference: https://x402.org / https://github.com/coinbase/x402
"""

import uuid
import time
import json
import hashlib
from datetime import datetime, timezone
from typing import Optional

from audit.logger import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── x402 Payment Requirements ──────────────────────────────────────

PREMIUM_RESOURCES = {
    "premium-catalog": {
        "description": "AI-optimized premium catalog with demand forecasting and pricing intelligence",
        "amount": 100,  # ₹1 in paise
        "currency": "INR",
        "resource": "/api/x402/resource/premium-catalog",
    },
    "analytics-feed": {
        "description": "Real-time sales analytics and inventory intelligence feed",
        "amount": 250,
        "currency": "INR",
        "resource": "/api/x402/resource/analytics-feed",
    },
    "ai-pricing": {
        "description": "AI-driven dynamic pricing recommendations for the merchant",
        "amount": 500,
        "currency": "INR",
        "resource": "/api/x402/resource/ai-pricing",
    },
}


class X402Engine:
    """
    Manages the x402 payment flow:
      1. Client requests paid resource → 402 response with requirements
      2. Client (AI agent) creates payment and sends proof in header
      3. Server verifies proof → returns resource + receipt
    """

    def __init__(self):
        # In-flight payment challenges: token → {resource, amount, expires_at}
        self._challenges: dict[str, dict] = {}
        # Completed payments: receipt_id → details
        self._receipts: list[dict] = []

    def create_payment_requirement(self, resource_key: str, requester_id: str = "agent") -> dict:
        """
        Generate a 402 payment requirement for a resource.
        This is what the server sends back when an unpaid resource is requested.
        """
        resource = PREMIUM_RESOURCES.get(resource_key)
        if not resource:
            return None

        payment_token = f"x402_tok_{uuid.uuid4().hex[:16]}"
        nonce = uuid.uuid4().hex
        expires_at = time.time() + 300  # 5 min window

        self._challenges[payment_token] = {
            "resource_key": resource_key,
            "amount": resource["amount"],
            "currency": resource["currency"],
            "requester_id": requester_id,
            "nonce": nonce,
            "created_at": time.time(),
            "expires_at": expires_at,
        }

        log_event(
            actor="ap2_protocol",
            action="x402_challenge_issued",
            reason=f"x402 challenge for resource '{resource_key}': {resource['description']} (₹{resource['amount']/100:.2f})",
        )

        return {
            "x402Version": "1.0",
            "protocol": "x402",
            "error": "Payment Required",
            "accepts": [
                {
                    "scheme": "exact",
                    "network": "razorpay-testmode",
                    "maxAmountRequired": str(resource["amount"] / 100),
                    "currency": resource["currency"],
                    "resource": resource["resource"],
                    "description": resource["description"],
                    "paymentToken": payment_token,
                    "nonce": nonce,
                    "expiresAt": _now_iso(),
                    "merchant": {
                        "name": "AgenticMart",
                        "identifier": "agenticmart_razorpay_test",
                    },
                }
            ],
            "paymentToken": payment_token,
            "instructions": (
                "To access this resource, create a Razorpay test-mode order "
                f"for ₹{resource['amount']/100:.2f} INR and send the order ID "
                "in the X-PAYMENT header as: "
                '{"network":"razorpay-testmode","paymentToken":"<token>","orderId":"<razorpay_order_id>"}'
            ),
        }

    def verify_payment(
        self,
        payment_header: dict,
        razorpay_order_id: Optional[str] = None,
    ) -> dict:
        """
        Verify a payment proof submitted via X-PAYMENT header.
        Returns {valid: bool, receipt_id: str, ...}
        """
        payment_token = payment_header.get("paymentToken", "")
        challenge = self._challenges.get(payment_token)

        if not challenge:
            return {"valid": False, "error": "Invalid or expired payment token"}

        if time.time() > challenge["expires_at"]:
            del self._challenges[payment_token]
            return {"valid": False, "error": "Payment token expired"}

        # In test mode: accept any Razorpay order ID as proof
        order_id = razorpay_order_id or payment_header.get("orderId", "")
        if not order_id:
            return {"valid": False, "error": "No Razorpay order ID provided"}

        receipt_id = f"x402_receipt_{uuid.uuid4().hex[:12]}"
        receipt = {
            "receiptId": receipt_id,
            "paymentToken": payment_token,
            "resourceKey": challenge["resource_key"],
            "amount": challenge["amount"],
            "currency": challenge["currency"],
            "network": "razorpay-testmode",
            "orderId": order_id,
            "requesterId": challenge["requester_id"],
            "settledAt": _now_iso(),
            "valid": True,
        }

        self._receipts.append(receipt)
        # Consume the challenge
        del self._challenges[payment_token]

        log_event(
            actor="ap2_protocol",
            action="x402_payment_verified",
            reason=f"x402 payment verified: resource '{challenge['resource_key']}', order {order_id}, receipt {receipt_id}",
            amount=challenge["amount"],
            rule_outcome="allowed",
        )

        return receipt

    def get_resource_content(self, resource_key: str) -> dict:
        """Return the actual paid resource content after successful payment."""
        if resource_key == "premium-catalog":
            from catalog.db import get_all_products
            products = get_all_products()
            return {
                "x402Resource": "premium-catalog",
                "accessedAt": _now_iso(),
                "pricingIntelligence": {
                    "demandForecast": "High demand for rice and dal products this week",
                    "recommendedUpsell": ["basmati_rice", "toor_dal"],
                    "peakHours": "18:00-21:00 IST",
                    "aiOptimizedPricing": True,
                },
                "products": products,
                "metadata": {
                    "totalProducts": len(products),
                    "protocol": "x402/1.0",
                    "contentType": "application/ld+json",
                },
            }
        elif resource_key == "analytics-feed":
            return {
                "x402Resource": "analytics-feed",
                "accessedAt": _now_iso(),
                "analytics": {
                    "topSellingCategory": "groceries",
                    "aiAgentOrderShare": "34%",
                    "avgOrderValue": "₹520",
                    "conversionRate": "68%",
                    "upsellAcceptanceRate": "42%",
                },
                "protocol": "x402/1.0",
            }
        elif resource_key == "ai-pricing":
            return {
                "x402Resource": "ai-pricing",
                "accessedAt": _now_iso(),
                "pricingRecommendations": [
                    {"productId": "basmati_rice", "currentPrice": 450, "recommendedPrice": 470, "confidence": 0.87},
                    {"productId": "toor_dal", "currentPrice": 180, "recommendedPrice": 195, "confidence": 0.91},
                    {"productId": "olive_oil", "currentPrice": 650, "recommendedPrice": 620, "confidence": 0.74},
                ],
                "protocol": "x402/1.0",
            }
        return {"error": "Unknown resource"}

    def get_receipts(self) -> list[dict]:
        return self._receipts

    def get_pending_challenges(self) -> list[dict]:
        now = time.time()
        return [
            {"paymentToken": k, **v}
            for k, v in self._challenges.items()
            if v["expires_at"] > now
        ]

    def reset(self):
        self._challenges.clear()
        self._receipts.clear()


# Global singleton
x402_engine = X402Engine()
