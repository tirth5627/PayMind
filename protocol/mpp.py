"""MPP — Machine Payments Protocol.

Implements Stripe + Tempo's MPP session model:
  POST   /api/mpp/session            → Create pre-authorized spending session
  GET    /api/mpp/session/{id}       → Get session + micropayment stream
  POST   /api/mpp/session/{id}/pay   → Stream a micropayment within the session
  DELETE /api/mpp/session/{id}       → Close session + settlement summary

Core primitive: Agents pre-authorize a spending LIMIT upfront and stream
granular micropayments within that session — no per-transaction overhead.

Reference: https://stripe.com/blog/mpp / Tempo mainnet March 2026
"""

import uuid
import time
from datetime import datetime, timezone
from typing import Optional

from audit.logger import log_event


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ── Rails ──────────────────────────────────────────────────────────

SUPPORTED_RAILS = {
    "razorpay": {
        "name": "Razorpay",
        "type": "fiat",
        "currency": "INR",
        "mode": "test",
        "description": "Razorpay test-mode fiat payments (INR)",
    },
    "usdc-base": {
        "name": "USDC on Base",
        "type": "stablecoin",
        "currency": "USDC",
        "mode": "simulated",
        "description": "USDC stablecoin on Base L2 (simulated)",
    },
}


# ── MPP Session ────────────────────────────────────────────────────

class MPPSession:
    """
    An MPP spending session — pre-authorized limit, streaming micropayments.
    """

    def __init__(
        self,
        agent_id: str,
        spending_limit: int,  # paise
        currency: str = "INR",
        rail: str = "razorpay",
        description: str = "",
    ):
        self.session_id = f"mpp_{uuid.uuid4().hex[:12]}"
        self.agent_id = agent_id
        self.spending_limit = spending_limit
        self.currency = currency
        self.rail = rail
        self.description = description
        self.status = "active"  # active | closed | limit_exceeded
        self.created_at = _now_iso()
        self.closed_at: Optional[str] = None
        self.micropayments: list[dict] = []
        self._total_spent = 0

    @property
    def total_spent(self) -> int:
        return self._total_spent

    @property
    def remaining(self) -> int:
        return max(0, self.spending_limit - self._total_spent)

    @property
    def utilization_pct(self) -> float:
        if self.spending_limit == 0:
            return 0.0
        return round(self._total_spent / self.spending_limit * 100, 1)

    def add_micropayment(
        self,
        amount: int,
        description: str,
        product_id: str = "",
        razorpay_order_id: str = "",
    ) -> dict:
        """Stream a micropayment within the session."""
        if self.status != "active":
            return {"error": f"Session is {self.status}, not active"}

        if amount > self.remaining:
            self.status = "limit_exceeded"
            return {
                "error": f"Payment ₹{amount/100:.2f} exceeds remaining limit ₹{self.remaining/100:.2f}",
                "sessionStatus": self.status,
            }

        payment_id = f"mp_{uuid.uuid4().hex[:10]}"
        payment = {
            "paymentId": payment_id,
            "sessionId": self.session_id,
            "amount": amount,
            "amountDisplay": f"₹{amount/100:.2f}",
            "currency": self.currency,
            "description": description,
            "productId": product_id,
            "razorpayOrderId": razorpay_order_id,
            "rail": self.rail,
            "streamedAt": _now_iso(),
            "runningTotal": self._total_spent + amount,
            "runningTotalDisplay": f"₹{(self._total_spent + amount)/100:.2f}",
        }

        self._total_spent += amount
        self.micropayments.append(payment)

        return payment

    def close(self) -> dict:
        """Close the session and return settlement summary."""
        self.status = "closed"
        self.closed_at = _now_iso()
        return self.to_dict()

    def to_dict(self) -> dict:
        return {
            "sessionId": self.session_id,
            "protocol": "MPP/1.0",
            "status": self.status,
            "agentId": self.agent_id,
            "rail": self.rail,
            "railDetails": SUPPORTED_RAILS.get(self.rail, {}),
            "spendingLimit": self.spending_limit,
            "spendingLimitDisplay": f"₹{self.spending_limit/100:.2f}",
            "totalSpent": self._total_spent,
            "totalSpentDisplay": f"₹{self._total_spent/100:.2f}",
            "remaining": self.remaining,
            "remainingDisplay": f"₹{self.remaining/100:.2f}",
            "utilizationPct": self.utilization_pct,
            "micropaymentCount": len(self.micropayments),
            "micropayments": self.micropayments,
            "createdAt": self.created_at,
            "closedAt": self.closed_at,
            "currency": self.currency,
            "description": self.description,
            "settlement": {
                "totalTransactions": len(self.micropayments),
                "totalAmount": self._total_spent,
                "totalAmountDisplay": f"₹{self._total_spent/100:.2f}",
                "averagePayment": (
                    round(self._total_spent / len(self.micropayments))
                    if self.micropayments else 0
                ),
                "settledVia": "Razorpay test-mode",
            } if self.status == "closed" else None,
        }


# ── MPP Engine ─────────────────────────────────────────────────────

class MPPEngine:
    """Manages MPP spending sessions."""

    def __init__(self):
        self._sessions: dict[str, MPPSession] = {}

    def create_session(
        self,
        agent_id: str,
        spending_limit: int,
        currency: str = "INR",
        rail: str = "razorpay",
        description: str = "",
    ) -> MPPSession:
        session = MPPSession(
            agent_id=agent_id,
            spending_limit=spending_limit,
            currency=currency,
            rail=rail,
            description=description,
        )
        self._sessions[session.session_id] = session

        log_event(
            actor="ap2_protocol",
            action="mpp_session_created",
            reason=f"MPP session {session.session_id} created for agent '{agent_id}': limit ₹{spending_limit/100:.2f} via {rail}",
            amount=spending_limit,
        )
        return session

    def get_session(self, session_id: str) -> Optional[MPPSession]:
        return self._sessions.get(session_id)

    def stream_payment(
        self,
        session_id: str,
        amount: int,
        description: str,
        product_id: str = "",
        razorpay_order_id: str = "",
    ) -> dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "Session not found"}

        result = session.add_micropayment(
            amount=amount,
            description=description,
            product_id=product_id,
            razorpay_order_id=razorpay_order_id,
        )

        if "error" not in result:
            log_event(
                actor="ap2_protocol",
                action="mpp_micropayment_streamed",
                reason=f"MPP micropayment {result['paymentId']}: ₹{amount/100:.2f} — {description}",
                amount=amount,
                rule_outcome="allowed",
            )
        else:
            log_event(
                actor="ap2_protocol",
                action="mpp_payment_rejected",
                reason=f"MPP session {session_id}: {result['error']}",
                amount=amount,
                rule_outcome="blocked",
            )

        return result

    def close_session(self, session_id: str) -> Optional[dict]:
        session = self._sessions.get(session_id)
        if not session:
            return None
        result = session.close()
        log_event(
            actor="ap2_protocol",
            action="mpp_session_closed",
            reason=f"MPP session {session_id} closed: {session.micropaymentCount if hasattr(session, 'micropaymentCount') else len(session.micropayments)} payments, ₹{session.total_spent/100:.2f} settled",
            amount=session.total_spent,
        )
        return result

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def reset(self):
        self._sessions.clear()


# Global singleton
mpp_engine = MPPEngine()
