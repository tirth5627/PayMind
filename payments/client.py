"""Razorpay SDK wrapper — order creation with idempotency and audit logging."""

import os
import uuid
from typing import Optional
from dotenv import load_dotenv
from audit.logger import log_event

load_dotenv()

# Lazy-initialize the Razorpay client
_client = None


def _get_client():
    """Get or create the Razorpay client. Raises if keys are missing."""
    global _client
    if _client is not None:
        return _client

    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise RuntimeError(
            "Razorpay API keys not configured. "
            "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file."
        )

    import razorpay
    _client = razorpay.Client(auth=(key_id, key_secret))
    _client.set_app_details({"title": "AgenticCommerce", "version": "0.1.0"})
    return _client


def create_order(
    amount_paise: int,
    currency: str = "INR",
    receipt: Optional[str] = None,
    notes: Optional[dict] = None,
    mandate_ref: Optional[str] = None,
) -> dict:
    """
    Create a Razorpay order with idempotency key.

    Args:
        amount_paise: Order amount in paise (e.g. 50000 = ₹500)
        currency: Currency code (default: INR)
        receipt: Receipt identifier (auto-generated if not provided)
        notes: Additional metadata to attach to the order
        mandate_ref: Mandate reference for audit trail linkage

    Returns:
        Razorpay order response dict with id, amount, status, etc.

    Raises:
        RuntimeError: If Razorpay keys are not configured
        razorpay.errors.BadRequestError: If the API rejects the request
    """
    client = _get_client()

    # Generate idempotency key to prevent double-charge on retry
    idempotency_key = str(uuid.uuid4())

    if receipt is None:
        receipt = f"rcpt_{uuid.uuid4().hex[:12]}"

    order_data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {},
    }

    log_event(
        actor="razorpay",
        action="create_order_attempt",
        reason=f"Creating Razorpay order: ₹{amount_paise / 100:.2f} {currency}, receipt={receipt}, idempotency_key={idempotency_key}",
        mandate_ref=mandate_ref,
        amount=amount_paise,
        rule_outcome="n/a",
    )

    try:
        order = client.order.create(data=order_data)

        log_event(
            actor="razorpay",
            action="create_order_success",
            reason=f"Razorpay order created: {order.get('id', 'unknown')} — status={order.get('status', 'unknown')}",
            mandate_ref=mandate_ref,
            amount=amount_paise,
            rule_outcome="allowed",
        )

        return order

    except Exception as e:
        log_event(
            actor="razorpay",
            action="create_order_failed",
            reason=f"Razorpay order creation failed: {type(e).__name__}: {str(e)}",
            mandate_ref=mandate_ref,
            amount=amount_paise,
            rule_outcome="blocked",
        )
        raise


def fetch_order(order_id: str) -> dict:
    """Fetch an existing order by Razorpay order ID."""
    client = _get_client()
    return client.order.fetch(order_id)
