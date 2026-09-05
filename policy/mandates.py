"""Mandate system — AP2-inspired Intent/Cart/Payment mandate chain.

Every purchase goes through three stages, each producing a traceable mandate object:
1. Intent Mandate: What the buyer asked for (raw + parsed)
2. Cart Mandate: Exact items and total the merchant proposes
3. Payment Mandate: The signed approval (or block) to charge

This mirrors Google AP2's cryptographic mandate pattern and NPCI UAP's
authorize-once-execute-many pattern.
"""

import uuid
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from audit.logger import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class IntentMandate:
    """What the buyer asked for."""
    id: str = field(default_factory=lambda: _gen_id("intent"))
    timestamp: str = field(default_factory=_now_iso)
    raw_request: str = ""          # buyer's exact words
    parsed_intent: str = ""        # agent's interpretation
    buyer_id: str = "human"        # "human" or "ai_buyer"
    status: str = "created"        # created → resolved

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": "intent", "timestamp": self.timestamp,
            "raw_request": self.raw_request, "parsed_intent": self.parsed_intent,
            "buyer_id": self.buyer_id, "status": self.status,
        }


@dataclass
class CartMandate:
    """Exact items + total the merchant proposes."""
    id: str = field(default_factory=lambda: _gen_id("cart"))
    timestamp: str = field(default_factory=_now_iso)
    intent_mandate_id: str = ""
    items: list = field(default_factory=list)  # list of dicts
    total_amount: int = 0           # paise
    currency: str = "INR"
    upsell_offered: list = field(default_factory=list)
    upsell_accepted: list = field(default_factory=list)
    status: str = "proposed"        # proposed → accepted → finalized

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": "cart", "timestamp": self.timestamp,
            "intent_mandate_id": self.intent_mandate_id,
            "items": self.items, "total_amount": self.total_amount,
            "total_display": f"₹{self.total_amount / 100:.2f}",
            "currency": self.currency, "status": self.status,
            "upsell_offered": self.upsell_offered,
            "upsell_accepted": self.upsell_accepted,
        }


@dataclass
class PaymentMandate:
    """The approval (or block) to charge."""
    id: str = field(default_factory=lambda: _gen_id("payment"))
    timestamp: str = field(default_factory=_now_iso)
    cart_mandate_id: str = ""
    intent_mandate_id: str = ""
    amount: int = 0                 # paise
    currency: str = "INR"
    policy_checks: list = field(default_factory=list)  # list of check results
    approved: bool = False
    approval_type: str = ""         # "automatic" or "explicit_buyer_override"
    razorpay_order_id: Optional[str] = None
    block_reasons: list = field(default_factory=list)
    status: str = "pending"         # pending → approved → blocked → completed → failed

    def to_dict(self) -> dict:
        return {
            "id": self.id, "type": "payment", "timestamp": self.timestamp,
            "cart_mandate_id": self.cart_mandate_id,
            "intent_mandate_id": self.intent_mandate_id,
            "amount": self.amount,
            "amount_display": f"₹{self.amount / 100:.2f}",
            "currency": self.currency,
            "policy_checks": self.policy_checks,
            "approved": self.approved, "approval_type": self.approval_type,
            "razorpay_order_id": self.razorpay_order_id,
            "block_reasons": self.block_reasons,
            "status": self.status,
        }


class MandateChain:
    """A complete mandate chain for one purchase attempt."""

    def __init__(self):
        self.intent: Optional[IntentMandate] = None
        self.cart: Optional[CartMandate] = None
        self.payment: Optional[PaymentMandate] = None

    def to_dict(self) -> dict:
        return {
            "intent": self.intent.to_dict() if self.intent else None,
            "cart": self.cart.to_dict() if self.cart else None,
            "payment": self.payment.to_dict() if self.payment else None,
        }


class MandateStore:
    """In-memory store for mandate chains with audit logging."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.chains: list[MandateChain] = []
        self.current_chain: Optional[MandateChain] = None

    def create_intent(self, raw_request: str, parsed_intent: str, buyer_id: str = "human") -> IntentMandate:
        """Start a new mandate chain with an intent."""
        chain = MandateChain()
        intent = IntentMandate(
            raw_request=raw_request,
            parsed_intent=parsed_intent,
            buyer_id=buyer_id,
        )
        chain.intent = intent
        self.current_chain = chain
        self.chains.append(chain)

        log_event(
            actor="gate",
            action="intent_mandate_created",
            reason=f"Intent: '{parsed_intent}' from {buyer_id}. Raw: '{raw_request[:100]}'",
            mandate_ref=intent.id,
        )
        return intent

    def create_cart(self, items: list[dict], total_amount: int, upsell_offered: list = None, upsell_accepted: list = None) -> CartMandate:
        """Create a cart mandate linked to the current intent."""
        if not self.current_chain or not self.current_chain.intent:
            raise ValueError("Cannot create cart mandate without an intent mandate")

        cart = CartMandate(
            intent_mandate_id=self.current_chain.intent.id,
            items=items,
            total_amount=total_amount,
            upsell_offered=upsell_offered or [],
            upsell_accepted=upsell_accepted or [],
        )
        self.current_chain.cart = cart
        self.current_chain.intent.status = "resolved"

        item_names = ", ".join(f"{i.get('quantity', 1)}x {i.get('name', '?')}" for i in items)
        log_event(
            actor="gate",
            action="cart_mandate_created",
            reason=f"Cart: {item_names} — Total: ₹{total_amount / 100:.2f}",
            mandate_ref=cart.id,
            amount=total_amount,
        )
        return cart

    def create_payment(self, policy_checks: list[dict], approved: bool, approval_type: str = "automatic", block_reasons: list = None) -> PaymentMandate:
        """Create a payment mandate linked to the current cart."""
        if not self.current_chain or not self.current_chain.cart:
            raise ValueError("Cannot create payment mandate without a cart mandate")

        payment = PaymentMandate(
            cart_mandate_id=self.current_chain.cart.id,
            intent_mandate_id=self.current_chain.intent.id,
            amount=self.current_chain.cart.total_amount,
            policy_checks=policy_checks,
            approved=approved,
            approval_type=approval_type,
            block_reasons=block_reasons or [],
            status="approved" if approved else "blocked",
        )
        self.current_chain.payment = payment
        self.current_chain.cart.status = "finalized"

        status_str = "APPROVED" if approved else "BLOCKED"
        reason_str = f"via {approval_type}"
        if block_reasons:
            reason_str += f" — blocks: {'; '.join(str(r) for r in block_reasons[:2])}"

        log_event(
            actor="gate",
            action="payment_mandate_created",
            reason=f"Payment: {status_str} for ₹{payment.amount / 100:.2f} {reason_str}",
            mandate_ref=payment.id,
            amount=payment.amount,
            rule_outcome="allowed" if approved else "blocked",
        )
        return payment

    def complete_payment(self, razorpay_order_id: str) -> None:
        """Mark the current payment mandate as completed with a Razorpay order ID."""
        if self.current_chain and self.current_chain.payment:
            self.current_chain.payment.razorpay_order_id = razorpay_order_id
            self.current_chain.payment.status = "completed"

            log_event(
                actor="gate",
                action="payment_mandate_completed",
                reason=f"Payment completed — Razorpay order: {razorpay_order_id}",
                mandate_ref=self.current_chain.payment.id,
                amount=self.current_chain.payment.amount,
                rule_outcome="allowed",
            )

    def approve_blocked(self, confirmation: str) -> Optional[PaymentMandate]:
        """Override a blocked payment mandate with explicit buyer approval."""
        if not self.current_chain or not self.current_chain.payment:
            return None
        if self.current_chain.payment.status != "blocked":
            return None

        self.current_chain.payment.approved = True
        self.current_chain.payment.approval_type = "explicit_buyer_override"
        self.current_chain.payment.status = "approved"

        log_event(
            actor="buyer",
            action="mandate_override",
            reason=f"Buyer explicitly approved blocked payment: '{confirmation}'",
            mandate_ref=self.current_chain.payment.id,
            amount=self.current_chain.payment.amount,
            rule_outcome="allowed",
        )
        return self.current_chain.payment

    def get_all_chains(self) -> list[dict]:
        """Get all mandate chains as dicts."""
        return [chain.to_dict() for chain in self.chains]

    def get_current_chain(self) -> Optional[dict]:
        """Get the current active chain."""
        if self.current_chain:
            return self.current_chain.to_dict()
        return None
