"""ACP — Agentic Commerce Protocol.

Implements OpenAI + Stripe's ACP specification:
  POST   /api/acp/checkout            → Create Checkout
  GET    /api/acp/checkout/{id}       → Get Checkout
  PUT    /api/acp/checkout/{id}       → Update Checkout
  DELETE /api/acp/checkout/{id}       → Cancel Checkout
  POST   /api/acp/checkout/{id}/complete → Complete + Razorpay order

SharedPaymentTokens are single-use, time-bound, amount-restricted
tokens that give users control while letting agents transact programmatically.

Reference: https://github.com/openai/acp-spec (Apache 2.0)
"""

import uuid
import time
import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from audit.logger import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _expires_iso(seconds: int = 300) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat().replace("+00:00", "Z")


# ── Shared Payment Token ───────────────────────────────────────────

class SharedPaymentToken:
    """
    Single-use, time-bound, amount-restricted payment token.
    The core security primitive in ACP.
    """

    def __init__(self, max_amount: int, currency: str = "INR", ttl: int = 300):
        self.token_id = f"spt_{secrets.token_urlsafe(16)}"
        self.max_amount = max_amount  # paise
        self.currency = currency
        self.created_at = time.time()
        self.expires_at = time.time() + ttl
        self.used = False
        self.used_amount: Optional[int] = None

    def is_valid(self, amount: int) -> tuple[bool, str]:
        if self.used:
            return False, "Token already used (single-use only)"
        if time.time() > self.expires_at:
            return False, "Token expired"
        if amount > self.max_amount:
            return False, f"Amount ₹{amount/100:.2f} exceeds token limit ₹{self.max_amount/100:.2f}"
        return True, "OK"

    def consume(self, amount: int):
        self.used = True
        self.used_amount = amount

    def to_dict(self) -> dict:
        return {
            "tokenId": self.token_id,
            "maxAmount": self.max_amount,
            "maxAmountDisplay": f"₹{self.max_amount/100:.2f}",
            "currency": self.currency,
            "expiresAt": datetime.fromtimestamp(self.expires_at, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
            "used": self.used,
            "singleUse": True,
        }


# ── Checkout Object ────────────────────────────────────────────────

class ACPCheckout:
    """
    ACP Checkout object — the central artifact of an agent checkout flow.
    Mirrors the ACP spec's Checkout data model.
    """

    STATUSES = ["pending", "confirmed", "completed", "cancelled"]

    def __init__(
        self,
        agent_id: str,
        items: list[dict],
        currency: str = "INR",
    ):
        self.checkout_id = f"chk_{uuid.uuid4().hex[:12]}"
        self.agent_id = agent_id
        self.items = items
        self.currency = currency
        self.status = "pending"
        self.created_at = _now_iso()
        self.updated_at = _now_iso()
        self.expires_at = _expires_iso(600)  # 10 min to complete
        self.razorpay_order_id: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.cancelled_reason: Optional[str] = None

        total = sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in items
        )
        self.total_paise = total
        # Issue a SharedPaymentToken (amount-restricted to the cart total)
        self.spt = SharedPaymentToken(max_amount=total + 10000)  # +₹100 buffer

    @property
    def total_display(self) -> str:
        return f"₹{self.total_paise / 100:.2f}"

    def to_dict(self) -> dict:
        return {
            "checkoutId": self.checkout_id,
            "protocol": "ACP/1.0",
            "status": self.status,
            "agentId": self.agent_id,
            "merchant": {
                "name": "AgenticMart",
                "identifier": "agenticmart_razorpay_test",
            },
            "items": self.items,
            "total": {
                "amount": self.total_paise / 100,
                "amountPaise": self.total_paise,
                "currency": self.currency,
                "display": self.total_display,
            },
            "sharedPaymentToken": self.spt.to_dict(),
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "expiresAt": self.expires_at,
            "razorpayOrderId": self.razorpay_order_id,
            "completedAt": self.completed_at,
            "cancelledReason": self.cancelled_reason,
            "links": {
                "self": f"/api/acp/checkout/{self.checkout_id}",
                "complete": f"/api/acp/checkout/{self.checkout_id}/complete",
                "cancel": f"/api/acp/checkout/{self.checkout_id}",
            },
        }


# ── ACP Engine ─────────────────────────────────────────────────────

class ACPEngine:
    """
    Manages ACP checkout sessions per the OpenAI/Stripe specification.
    """

    def __init__(self):
        self._checkouts: dict[str, ACPCheckout] = {}

    def create_checkout(
        self,
        agent_id: str,
        items: list[dict],
        currency: str = "INR",
    ) -> ACPCheckout:
        """POST /api/acp/checkout"""
        checkout = ACPCheckout(agent_id=agent_id, items=items, currency=currency)
        self._checkouts[checkout.checkout_id] = checkout

        log_event(
            actor="ap2_protocol",
            action="acp_checkout_created",
            reason=f"ACP Checkout {checkout.checkout_id} created for agent '{agent_id}': {len(items)} items, {checkout.total_display}",
            amount=checkout.total_paise,
        )
        return checkout

    def get_checkout(self, checkout_id: str) -> Optional[ACPCheckout]:
        """GET /api/acp/checkout/{id}"""
        return self._checkouts.get(checkout_id)

    def update_checkout(
        self,
        checkout_id: str,
        items: Optional[list[dict]] = None,
    ) -> Optional[ACPCheckout]:
        """PUT /api/acp/checkout/{id}"""
        checkout = self._checkouts.get(checkout_id)
        if not checkout or checkout.status not in ("pending",):
            return None

        if items is not None:
            checkout.items = items
            total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
            checkout.total_paise = total
            checkout.spt = SharedPaymentToken(max_amount=total + 10000)

        checkout.updated_at = _now_iso()
        log_event(
            actor="ap2_protocol",
            action="acp_checkout_updated",
            reason=f"ACP Checkout {checkout_id} updated: {len(checkout.items)} items",
        )
        return checkout

    def cancel_checkout(self, checkout_id: str, reason: str = "") -> Optional[ACPCheckout]:
        """DELETE /api/acp/checkout/{id}"""
        checkout = self._checkouts.get(checkout_id)
        if not checkout or checkout.status == "completed":
            return None

        checkout.status = "cancelled"
        checkout.cancelled_reason = reason
        checkout.updated_at = _now_iso()

        log_event(
            actor="ap2_protocol",
            action="acp_checkout_cancelled",
            reason=f"ACP Checkout {checkout_id} cancelled: {reason}",
        )
        return checkout

    def complete_checkout(
        self,
        checkout_id: str,
        razorpay_order_id: str,
        amount_paid: int,
    ) -> Optional[dict]:
        """POST /api/acp/checkout/{id}/complete"""
        checkout = self._checkouts.get(checkout_id)
        if not checkout:
            return {"error": "Checkout not found"}
        if checkout.status != "pending":
            return {"error": f"Cannot complete a checkout in '{checkout.status}' state"}

        # Validate SharedPaymentToken
        valid, reason = checkout.spt.is_valid(amount_paid)
        if not valid:
            log_event(
                actor="ap2_protocol",
                action="acp_spt_rejected",
                reason=f"SharedPaymentToken rejected for checkout {checkout_id}: {reason}",
                rule_outcome="blocked",
            )
            return {"error": f"Payment token rejected: {reason}"}

        # Consume the token and complete
        checkout.spt.consume(amount_paid)
        checkout.status = "completed"
        checkout.razorpay_order_id = razorpay_order_id
        checkout.completed_at = _now_iso()
        checkout.updated_at = _now_iso()

        log_event(
            actor="ap2_protocol",
            action="acp_checkout_completed",
            reason=f"ACP Checkout {checkout_id} completed: Razorpay {razorpay_order_id}, ₹{amount_paid/100:.2f}",
            amount=amount_paid,
            rule_outcome="allowed",
        )

        return checkout.to_dict()

    def list_checkouts(self) -> list[dict]:
        return [c.to_dict() for c in self._checkouts.values()]

    def reset(self):
        self._checkouts.clear()


# Global singleton
acp_engine = ACPEngine()
