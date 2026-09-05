"""AP2 Protocol Simulator — Agent-to-Agent Payment Protocol.

Implements the 6-phase AP2 (Agent Payment Protocol v2) flow:
  DISCOVER → NEGOTIATE → INTENT_LOCK → POLICY_GATE → PAYMENT → SETTLEMENT

Each phase emits structured trace events with timing, participant IDs,
and cryptographic references. This creates a visual, auditable handshake
between two autonomous agents transacting through Razorpay.
"""

import time
import uuid
import hashlib
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

from audit.logger import log_event


class AP2Phase(str, Enum):
    DISCOVER = "DISCOVER"
    NEGOTIATE = "NEGOTIATE"
    INTENT_LOCK = "INTENT_LOCK"
    POLICY_GATE = "POLICY_GATE"
    PAYMENT = "PAYMENT"
    SETTLEMENT = "SETTLEMENT"


AP2_PHASE_META = {
    AP2Phase.DISCOVER: {
        "label": "Discover",
        "icon": "🔍",
        "description": "Buyer agent discovers merchant catalog via agent-readable endpoint",
    },
    AP2Phase.NEGOTIATE: {
        "label": "Negotiate",
        "icon": "🤝",
        "description": "Buyer and merchant agents negotiate items, quantities, and pricing",
    },
    AP2Phase.INTENT_LOCK: {
        "label": "Intent Lock",
        "icon": "🔒",
        "description": "Buyer's purchase intent is cryptographically locked into the mandate chain",
    },
    AP2Phase.POLICY_GATE: {
        "label": "Policy Gate",
        "icon": "🛡️",
        "description": "Spend caps, category rules, and compliance checks are evaluated",
    },
    AP2Phase.PAYMENT: {
        "label": "Payment",
        "icon": "💳",
        "description": "Razorpay order created and payment is processed via test-mode API",
    },
    AP2Phase.SETTLEMENT: {
        "label": "Settlement",
        "icon": "✅",
        "description": "Transaction settled, audit trail sealed, mandate chain completed",
    },
}


@dataclass
class AP2TraceStep:
    """A single step in the AP2 protocol trace."""
    phase: str
    status: str  # "pending" | "active" | "completed" | "failed" | "recovered"
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    participant: Optional[str] = None
    detail: Optional[str] = None
    hash_ref: Optional[str] = None
    failure_reason: Optional[str] = None
    recovery_action: Optional[str] = None

    def to_dict(self):
        d = asdict(self)
        meta = AP2_PHASE_META.get(AP2Phase(self.phase), {})
        d["label"] = meta.get("label", self.phase)
        d["icon"] = meta.get("icon", "⚙️")
        d["description"] = meta.get("description", "")
        return d


@dataclass
class AP2Trace:
    """Full AP2 protocol trace for a single transaction."""
    trace_id: str = field(default_factory=lambda: f"ap2_{uuid.uuid4().hex[:12]}")
    buyer_agent: str = ""
    merchant_agent: str = "AgenticMart"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "in_progress"  # in_progress | completed | failed
    steps: list = field(default_factory=list)
    razorpay_order_id: Optional[str] = None

    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "buyer_agent": self.buyer_agent,
            "merchant_agent": self.merchant_agent,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "status": self.status,
            "total_duration_ms": (
                (self.completed_at - self.started_at) * 1000
                if self.completed_at
                else (time.time() - self.started_at) * 1000
            ),
            "razorpay_order_id": self.razorpay_order_id,
            "steps": [s.to_dict() for s in self.steps],
            "phase_count": len(self.steps),
            "completed_phases": sum(
                1 for s in self.steps if s.status in ("completed", "recovered")
            ),
        }


def _make_hash(data: str) -> str:
    """Create a short SHA-256 hash for audit references."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class AP2ProtocolEngine:
    """Manages AP2 protocol traces across sessions."""

    def __init__(self):
        self._traces: list[AP2Trace] = []
        self._current: Optional[AP2Trace] = None

    def get_current_trace(self) -> Optional[dict]:
        if self._current:
            return self._current.to_dict()
        return None

    def get_all_traces(self) -> list[dict]:
        return [t.to_dict() for t in self._traces]

    def start_trace(self, buyer_agent: str = "human") -> AP2Trace:
        """Start a new AP2 protocol trace."""
        trace = AP2Trace(buyer_agent=buyer_agent)

        # Initialize all 6 phases as pending
        for phase in AP2Phase:
            trace.steps.append(AP2TraceStep(phase=phase.value, status="pending"))

        self._current = trace
        self._traces.append(trace)

        log_event(
            actor="ap2_protocol",
            action="trace_started",
            reason=f"AP2 trace {trace.trace_id} started for buyer '{buyer_agent}'",
        )
        return trace

    def advance_phase(
        self,
        phase: AP2Phase,
        participant: str = "",
        detail: str = "",
        success: bool = True,
        failure_reason: str = "",
        recovery_action: str = "",
    ) -> Optional[AP2TraceStep]:
        """Advance a specific phase in the current trace."""
        if not self._current:
            return None

        step = None
        for s in self._current.steps:
            if s.phase == phase.value:
                step = s
                break

        if not step:
            return None

        now = time.time()
        step.started_at = step.started_at or now
        step.participant = participant
        step.detail = detail
        step.hash_ref = _make_hash(
            f"{self._current.trace_id}:{phase.value}:{now}"
        )

        if success:
            step.status = "completed"
            step.completed_at = now
            step.duration_ms = round((now - step.started_at) * 1000, 1)
        else:
            step.status = "failed"
            step.failure_reason = failure_reason
            if recovery_action:
                step.recovery_action = recovery_action
                step.status = "recovered"
                step.completed_at = now
                step.duration_ms = round((now - step.started_at) * 1000, 1)

        # Mark the next phase as active
        found_current = False
        for s in self._current.steps:
            if s.phase == phase.value:
                found_current = True
                continue
            if found_current and s.status == "pending" and success:
                s.status = "active"
                s.started_at = now
                break

        # Check if all phases complete
        all_done = all(
            s.status in ("completed", "recovered", "failed")
            for s in self._current.steps
        )
        if all_done:
            self._current.status = "completed"
            self._current.completed_at = now

        log_event(
            actor="ap2_protocol",
            action=f"phase_{phase.value.lower()}",
            reason=detail or f"Phase {phase.value} {'completed' if success else 'failed'}",
            rule_outcome="allowed" if success else "blocked",
        )

        return step

    def set_active(self, phase: AP2Phase):
        """Mark a phase as actively processing."""
        if not self._current:
            return
        for s in self._current.steps:
            if s.phase == phase.value:
                s.status = "active"
                s.started_at = s.started_at or time.time()
                break

    def complete_trace(self, razorpay_order_id: str = ""):
        """Mark the current trace as fully completed."""
        if self._current:
            self._current.completed_at = time.time()
            self._current.status = "completed"
            self._current.razorpay_order_id = razorpay_order_id

            log_event(
                actor="ap2_protocol",
                action="trace_completed",
                reason=f"AP2 trace {self._current.trace_id} finalized (Razorpay: {razorpay_order_id})",
            )

    def clear_trace(self):
        """Clear the current trace so a new one can begin."""
        self._current = None

    def reset(self):
        """Reset all traces."""
        self._traces.clear()
        self._current = None


# Global singleton
ap2_engine = AP2ProtocolEngine()
