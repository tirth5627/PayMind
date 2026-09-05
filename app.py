"""AgenticMart — Web Dashboard & API Server.

Single FastAPI server serving:
- The Next.js frontend (proxied in dev, or served from `frontend/out` in prod)
- Chat API (POST /api/chat)
- Session state API (GET /api/session)
- Audit log API (GET /api/audit)
- AI Buyer demo API (POST /api/ai-buyer/start, GET /api/ai-buyer/status)
- Risk scoring API (GET /api/risk-score)
- Mandate report API (GET /api/mandate-report)
- WebSocket (WS /ws) — real-time event streaming
"""

import asyncio
import sys
import os
import json
import queue
import time
import threading
from typing import Optional

# Fix Windows encoding
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.setup import init_db
from orchestrator.agent import OrchestratorAgent
from audit.db import get_recent_events, clear_audit_log
from buyer_agent.agent import AIBuyerAgent, BUYER_PERSONAS
from risk.scorer import compute_risk_score, get_category_breakdown
from protocol.ap2 import ap2_engine
from protocol.ap2_mandate import ap2_mandate_engine
from protocol.x402 import x402_engine
from protocol.acp import acp_engine
from protocol.mpp import mpp_engine
from catalog.jsonld import get_catalog_jsonld, get_product_jsonld

# Initialize database
init_db()

# FastAPI app
app = FastAPI(title="AgenticMart", description="Agentic Commerce — AI Payment Governance Layer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── WebSocket connection manager ──────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._event_queue: queue.Queue = queue.Queue()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)

    def push_event(self, event: dict):
        """Thread-safe push from synchronous code."""
        self._event_queue.put_nowait(json.dumps(event))

    async def flush_queue(self):
        """Drain sync queue → broadcast to all WebSocket clients."""
        while not self._event_queue.empty():
            try:
                msg = self._event_queue.get_nowait()
                await self.broadcast(msg)
            except Exception:
                break


ws_manager = ConnectionManager()


# Background task: flush event queue every 200ms
async def _event_flusher():
    while True:
        await ws_manager.flush_queue()
        await asyncio.sleep(0.2)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(_event_flusher())


# ── Session state ─────────────────────────────────────────────────

_agent: Optional[OrchestratorAgent] = None
_ai_buyer: Optional[AIBuyerAgent] = None
_ai_buyer_thread = None
_blocked_attempts: int = 0
_override_count: int = 0


def _get_agent() -> OrchestratorAgent:
    global _agent
    if _agent is None:
        _agent = OrchestratorAgent(buyer_id="human")
    return _agent


# ── API Models ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str


class AIBuyerRequest(BaseModel):
    persona: str = "grocery_shopper"


# ── WebSocket endpoint ────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send connected confirmation
        await websocket.send_text(json.dumps({"type": "connected", "message": "PayMind stream active"}))
        # Keep alive + drain queue
        while True:
            await ws_manager.flush_queue()
            try:
                # Non-blocking check for client messages
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Routes ────────────────────────────────────────────────────────

@app.get("/")
async def root():
    static_index = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "out", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return JSONResponse({"status": "AgenticMart API running", "docs": "/docs", "message": "Run npm run build in frontend directory"})


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Send a message to the orchestrator agent."""
    global _blocked_attempts, _override_count

    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    agent = _get_agent()

    # Broadcast user message event
    ws_manager.push_event({
        "type": "chat_message",
        "role": "user",
        "message": request.message,
        "timestamp": time.time(),
    })

    try:
        response = await asyncio.to_thread(agent.chat, request.message)
        session = agent.get_session_state()

        # Detect blocks / overrides from response
        if "blocked" in response.lower() or "⚠️" in response:
            _blocked_attempts += 1
        if "approved" in response.lower() or "override" in response.lower():
            _override_count += 1

        # Broadcast agent response
        ws_manager.push_event({
            "type": "chat_message",
            "role": "agent",
            "message": response,
            "session": session,
            "timestamp": time.time(),
        })

        # Broadcast session update
        ws_manager.push_event({
            "type": "session_update",
            "session": session,
            "timestamp": time.time(),
        })

        return {
            "response": response,
            "session": session,
        }
    except Exception as e:
        ws_manager.push_event({
            "type": "error",
            "message": str(e),
            "timestamp": time.time(),
        })
        return {
            "response": f"❌ Error: {type(e).__name__}: {str(e)}",
            "session": agent.get_session_state(),
            "error": True,
        }


@app.get("/api/session")
async def session():
    """Get current session state."""
    agent = _get_agent()
    return agent.get_session_state()


@app.post("/api/session/reset")
async def reset_session():
    """Reset the shopping session."""
    global _agent, _blocked_attempts, _override_count, _ai_buyer
    _agent = OrchestratorAgent(buyer_id="human")
    _ai_buyer = None
    _blocked_attempts = 0
    _override_count = 0
    clear_audit_log()
    
    from protocol.ap2 import ap2_engine
    ap2_engine.clear_trace()
    
    session = _agent.get_session_state()
    ws_manager.push_event({"type": "session_reset", "session": session, "timestamp": time.time()})
    return {"message": "Session reset", "session": session}


@app.get("/api/audit")
async def audit(limit: int = 100):
    """Get recent audit log entries."""
    events = get_recent_events(limit)
    return {"events": list(reversed(events)), "count": len(events)}


@app.get("/api/risk-score")
async def risk_score():
    """Compute real-time risk score for the current session."""
    agent = _get_agent()
    session = agent.get_session_state()

    cart_items = session.get("cart", {}).get("items", [])
    cart_total = session.get("cart", {}).get("total", 0)
    session_spent = session.get("session_spent", 0)

    score = compute_risk_score(
        session_spent=session_spent,
        cart_total=cart_total,
        cart_items=cart_items,
        blocked_attempts=_blocked_attempts,
        override_count=_override_count,
    )
    category_breakdown = get_category_breakdown(cart_items)

    return {**score, "category_breakdown": category_breakdown}


@app.get("/api/mandate-report")
async def mandate_report():
    """Generate a structured mandate compliance report for all session orders."""
    agent = _get_agent()
    session = agent.get_session_state()
    audit_events = get_recent_events(500)

    return {
        "report_generated_at": time.time(),
        "session_id": session.get("session_id"),
        "buyer_id": session.get("buyer_id"),
        "summary": {
            "total_orders": len(session.get("orders", [])),
            "total_spent": session.get("session_spent"),
            "total_spent_display": session.get("session_spent_display"),
            "spend_cap": session.get("session_cap"),
            "spend_cap_display": session.get("session_cap_display"),
            "utilization_pct": session.get("spend_pct"),
            "blocked_attempts": _blocked_attempts,
            "overrides_granted": _override_count,
            "upsell_acceptance_rate": session.get("upsell", {}).get("acceptance_rate_display"),
        },
        "orders": session.get("orders", []),
        "mandate_chains": session.get("mandates", []),
        "audit_events_count": len(audit_events),
        "compliance_status": "COMPLIANT" if _blocked_attempts == 0 else "REVIEWED",
    }


@app.get("/api/personas")
async def personas():
    """Get available AI buyer personas."""
    return {
        "personas": {
            key: {
                "name": p["name"],
                "goal": p["goal"],
                "budget": p["budget"],
                "style": p["style"],
                "emoji": p.get("emoji", "🤖"),
                "description": p.get("description", ""),
            }
            for key, p in BUYER_PERSONAS.items()
        }
    }


@app.post("/api/ai-buyer/start")
async def start_ai_buyer(request: AIBuyerRequest):
    """Launch an AI buyer agent demo."""
    global _ai_buyer, _ai_buyer_thread

    if _ai_buyer and _ai_buyer.status == "running":
        raise HTTPException(status_code=409, detail="AI buyer is already running")

    persona_key = request.persona
    if persona_key not in BUYER_PERSONAS:
        raise HTTPException(status_code=400, detail=f"Unknown persona: {persona_key}")

    # Create a thread-safe queue for WS events
    import queue as q_mod
    ws_q = q_mod.Queue()

    _ai_buyer = AIBuyerAgent(persona_key=persona_key, ws_queue=ws_manager._event_queue)

    ws_manager.push_event({
        "type": "ai_buyer_started",
        "persona": _ai_buyer.persona,
        "persona_key": persona_key,
        "timestamp": time.time(),
    })

    _ai_buyer_thread = _ai_buyer.run_async()

    return {
        "message": f"AI Buyer '{_ai_buyer.persona['name']}' started",
        "persona": _ai_buyer.persona,
        "status": _ai_buyer.status,
    }


@app.get("/api/ai-buyer/status")
async def ai_buyer_status():
    """Get AI buyer progress."""
    if _ai_buyer is None:
        return {"status": "idle", "conversation": [], "result": None}

    return {
        "status": _ai_buyer.status,
        "persona": _ai_buyer.persona,
        "conversation": _ai_buyer.conversation,
        "result": _ai_buyer.result,
    }


# ── AP2 Protocol endpoints ────────────────────────────────────────

@app.get("/api/protocol/trace")
async def protocol_trace():
    """Get the current AP2 protocol trace."""
    current = ap2_engine.get_current_trace()
    all_traces = ap2_engine.get_all_traces()
    return {
        "current_trace": current,
        "all_traces": all_traces,
        "trace_count": len(all_traces),
    }


# ── AP2 Mandate endpoints (ECDSA-signed JSON-LD) ──────────────────

@app.get("/api/ap2/mandates")
async def get_ap2_mandates():
    """Get all signed AP2 mandates for the current session."""
    agent = _get_agent()
    session_id = agent.session_id
    mandates = ap2_mandate_engine.get_session_mandates(session_id)
    all_mandates = ap2_mandate_engine.get_all_mandates()
    return {
        "sessionId": session_id,
        "sessionMandates": mandates,
        "sessionMandateCount": len(mandates),
        "totalMandates": len(all_mandates),
        "protocol": "AP2/1.0",
        "signatureAlgorithm": "ECDSA-P256-SHA256",
        "cryptoAvailable": True,
    }


@app.post("/api/ap2/mandate/verify")
async def verify_ap2_mandate(body: dict):
    """Verify a signed AP2 mandate's ECDSA signature."""
    result = ap2_mandate_engine.verify_mandate(body)
    return result


# ── x402 Protocol endpoints ───────────────────────────────────────

class X402PaymentBody(BaseModel):
    paymentToken: str
    orderId: str = ""
    network: str = "razorpay-testmode"


@app.get("/api/x402/resource/{resource_key}")
async def x402_resource(resource_key: str, x_payment: Optional[str] = None):
    """
    x402 paid resource endpoint.
    - Without X-PAYMENT header: returns HTTP 402 with payment requirements.
    - With valid X-PAYMENT header: returns the paid resource content.
    """
    from fastapi import Header
    from fastapi.responses import JSONResponse as JR

    if not x_payment:
        # Step 1: Return 402 with payment requirements
        requirement = x402_engine.create_payment_requirement(resource_key)
        if not requirement:
            raise HTTPException(status_code=404, detail=f"Resource '{resource_key}' not found")
        return JR(content=requirement, status_code=402)

    # Step 2: Verify payment and return resource
    try:
        payment_data = json.loads(x_payment)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid X-PAYMENT header JSON")

    receipt = x402_engine.verify_payment(payment_data)
    if not receipt.get("valid"):
        raise HTTPException(status_code=402, detail=receipt.get("error", "Payment verification failed"))

    content = x402_engine.get_resource_content(resource_key)
    return JR(
        content={"receipt": receipt, "resource": content},
        headers={"X-PAYMENT-RESPONSE": json.dumps({"success": True, "receiptId": receipt["receiptId"]})},
    )


@app.get("/api/x402/status")
async def x402_status():
    """Get x402 protocol status — pending challenges and completed receipts."""
    return {
        "protocol": "x402/1.0",
        "pendingChallenges": x402_engine.get_pending_challenges(),
        "completedReceipts": x402_engine.get_receipts(),
        "availableResources": [
            {"key": k, "description": v["description"], "amount": v["amount"], "currency": v["currency"]}
            for k, v in __import__('protocol.x402', fromlist=['PREMIUM_RESOURCES']).PREMIUM_RESOURCES.items()
        ],
    }


@app.post("/api/x402/pay")
async def x402_pay(body: X402PaymentBody):
    """Verify an x402 payment proof (used after Razorpay order creation)."""
    receipt = x402_engine.verify_payment(
        {"paymentToken": body.paymentToken, "network": body.network},
        razorpay_order_id=body.orderId,
    )
    return receipt


# ── ACP Checkout endpoints ────────────────────────────────────────

class ACPCreateCheckoutBody(BaseModel):
    agentId: str = "human_agent"
    items: list
    currency: str = "INR"


class ACPUpdateCheckoutBody(BaseModel):
    items: Optional[list] = None


class ACPCompleteBody(BaseModel):
    razorpayOrderId: str
    amountPaid: int


@app.post("/api/acp/checkout")
async def acp_create_checkout(body: ACPCreateCheckoutBody):
    """ACP: Create Checkout."""
    checkout = acp_engine.create_checkout(
        agent_id=body.agentId,
        items=body.items,
        currency=body.currency,
    )
    return checkout.to_dict()


@app.get("/api/acp/checkout/{checkout_id}")
async def acp_get_checkout(checkout_id: str):
    """ACP: Get Checkout."""
    checkout = acp_engine.get_checkout(checkout_id)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found")
    return checkout.to_dict()


@app.put("/api/acp/checkout/{checkout_id}")
async def acp_update_checkout(checkout_id: str, body: ACPUpdateCheckoutBody):
    """ACP: Update Checkout (change items)."""
    checkout = acp_engine.update_checkout(checkout_id, items=body.items)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found or not updatable")
    return checkout.to_dict()


@app.delete("/api/acp/checkout/{checkout_id}")
async def acp_cancel_checkout(checkout_id: str, reason: str = ""):
    """ACP: Cancel Checkout."""
    checkout = acp_engine.cancel_checkout(checkout_id, reason)
    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found or already completed")
    return checkout.to_dict()


@app.post("/api/acp/checkout/{checkout_id}/complete")
async def acp_complete_checkout(checkout_id: str, body: ACPCompleteBody):
    """ACP: Complete Checkout — validates SharedPaymentToken + triggers Razorpay order."""
    result = acp_engine.complete_checkout(
        checkout_id=checkout_id,
        razorpay_order_id=body.razorpayOrderId,
        amount_paid=body.amountPaid,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/api/acp/checkouts")
async def acp_list_checkouts():
    """List all ACP checkout sessions."""
    return {"checkouts": acp_engine.list_checkouts(), "protocol": "ACP/1.0"}


# ── MPP Session endpoints ─────────────────────────────────────────

class MPPCreateSessionBody(BaseModel):
    agentId: str = "human_agent"
    spendingLimit: int  # paise
    currency: str = "INR"
    rail: str = "razorpay"
    description: str = ""


class MPPMicropaymentBody(BaseModel):
    amount: int  # paise
    description: str
    productId: str = ""
    razorpayOrderId: str = ""


@app.post("/api/mpp/session")
async def mpp_create_session(body: MPPCreateSessionBody):
    """MPP: Create a pre-authorized spending session."""
    session = mpp_engine.create_session(
        agent_id=body.agentId,
        spending_limit=body.spendingLimit,
        currency=body.currency,
        rail=body.rail,
        description=body.description,
    )
    return session.to_dict()


@app.get("/api/mpp/session/{session_id}")
async def mpp_get_session(session_id: str):
    """MPP: Get session state + micropayment stream."""
    session = mpp_engine.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="MPP session not found")
    return session.to_dict()


@app.post("/api/mpp/session/{session_id}/pay")
async def mpp_stream_payment(session_id: str, body: MPPMicropaymentBody):
    """MPP: Stream a micropayment within the pre-authorized session."""
    result = mpp_engine.stream_payment(
        session_id=session_id,
        amount=body.amount,
        description=body.description,
        product_id=body.productId,
        razorpay_order_id=body.razorpayOrderId,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.delete("/api/mpp/session/{session_id}")
async def mpp_close_session(session_id: str):
    """MPP: Close session and return settlement summary."""
    result = mpp_engine.close_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="MPP session not found")
    return result


@app.get("/api/mpp/sessions")
async def mpp_list_sessions():
    """List all MPP sessions."""
    return {"sessions": mpp_engine.list_sessions(), "protocol": "MPP/1.0"}


# ── Protocol Overview ─────────────────────────────────────────────

@app.get("/api/protocols")
async def protocols_overview():
    """Overview of all 4 implemented agentic payment protocols."""
    agent = _get_agent()
    return {
        "ap2": {
            "name": "Agent Payments Protocol",
            "version": "AP2/1.0",
            "developer": "Google + 60 partners",
            "layer": "Authorization & Trust",
            "description": "Cryptographically signed ECDSA mandates — the trust layer for agent payments",
            "status": "active",
            "mandateCount": len(ap2_mandate_engine.get_session_mandates(agent.session_id)),
            "signatureAlgorithm": "ECDSA-P256-SHA256",
            "endpoints": ["/api/ap2/mandates", "/api/ap2/mandate/verify", "/api/protocol/trace"],
        },
        "x402": {
            "name": "x402 Payment Protocol",
            "version": "x402/1.0",
            "developer": "Coinbase",
            "layer": "Execution & Settlement",
            "description": "HTTP 402-based instant payments — machine-to-machine pay-per-resource",
            "status": "active",
            "pendingChallenges": len(x402_engine.get_pending_challenges()),
            "completedReceipts": len(x402_engine.get_receipts()),
            "endpoints": ["/api/x402/resource/{key}", "/api/x402/pay", "/api/x402/status"],
        },
        "acp": {
            "name": "Agentic Commerce Protocol",
            "version": "ACP/1.0",
            "developer": "OpenAI + Stripe",
            "layer": "Checkout & Merchant Integration",
            "description": "4-endpoint checkout flow with SharedPaymentTokens — standardized agent-merchant commerce",
            "status": "active",
            "activeCheckouts": len([c for c in acp_engine.list_checkouts() if c["status"] == "pending"]),
            "completedCheckouts": len([c for c in acp_engine.list_checkouts() if c["status"] == "completed"]),
            "endpoints": ["/api/acp/checkout", "/api/acp/checkout/{id}", "/api/acp/checkout/{id}/complete"],
        },
        "mpp": {
            "name": "Machine Payments Protocol",
            "version": "MPP/1.0",
            "developer": "Stripe + Tempo",
            "layer": "Session & Micropayments",
            "description": "Pre-authorized spending sessions with streaming micropayments — no per-transaction overhead",
            "status": "active",
            "activeSessions": len([s for s in mpp_engine.list_sessions() if s["status"] == "active"]),
            "totalMicropayments": sum(s["micropaymentCount"] for s in mpp_engine.list_sessions()),
            "endpoints": ["/api/mpp/session", "/api/mpp/session/{id}/pay", "/api/mpp/sessions"],
        },
    }



# ── Agent-Readable Catalog (JSON-LD) ──────────────────────────────

@app.get("/api/catalog/agent-readable")
async def agent_readable_catalog():
    """Serve the merchant catalog as Schema.org JSON-LD for AI agent discovery."""
    return JSONResponse(
        content=get_catalog_jsonld(),
        media_type="application/ld+json",
    )


@app.get("/api/catalog/agent-readable/{product_id}")
async def agent_readable_product(product_id: str):
    """Serve a single product as Schema.org JSON-LD."""
    product = get_product_jsonld(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return JSONResponse(content=product, media_type="application/ld+json")


# ── Revenue Growth Metrics ────────────────────────────────────────

@app.get("/api/revenue/metrics")
async def revenue_metrics():
    """Aggregate revenue metrics to show AI-driven merchant growth."""
    agent = _get_agent()
    session = agent.get_session_state()
    audit_events = get_recent_events(1000)

    # Get all successful checkouts
    checkout_events = [e for e in audit_events if e.get("action") == "checkout_complete"]
    total_revenue = sum(e.get("amount", 0) for e in checkout_events)
    
    ai_revenue = sum(e.get("amount", 0) for e in checkout_events if e.get("actor") == "ai_buyer")
    human_revenue = sum(e.get("amount", 0) for e in checkout_events if e.get("actor") == "buyer")

    ai_orders = [e for e in audit_events if e.get("actor") == "ai_buyer" and e.get("action") == "message"]
    human_orders = [e for e in audit_events if e.get("actor") == "buyer" and e.get("action") == "message"]

    # Campaign savings
    campaign_events = [e for e in audit_events if e.get("action") == "campaign_applied"]
    total_campaign_savings = sum(e.get("amount", 0) for e in campaign_events)

    # Upsell metrics (still pulled from current session for simplicity)
    upsell_data = session.get("upsell", {})

    return {
        "total_revenue": total_revenue,
        "total_revenue_display": f"\u20b9{total_revenue / 100:.2f}",
        "order_count": len(checkout_events),
        "ai_revenue": ai_revenue,
        "ai_revenue_display": f"\u20b9{ai_revenue / 100:.2f}",
        "human_revenue": human_revenue,
        "human_revenue_display": f"\u20b9{human_revenue / 100:.2f}",
        "ai_revenue_pct": round(ai_revenue / total_revenue * 100, 1) if total_revenue > 0 else 0,
        "campaign_savings": total_campaign_savings,
        "campaign_savings_display": f"\u20b9{total_campaign_savings / 100:.2f}",
        "campaign_count": len(campaign_events),
        "upsell_offered": upsell_data.get("offered", 0),
        "upsell_accepted": upsell_data.get("accepted", 0),
        "upsell_rate": upsell_data.get("acceptance_rate_display", "0%"),
        "blocked_attempts": _blocked_attempts,
        "overrides": _override_count,
        "protocol_traces": len(ap2_engine.get_all_traces()),
    }


# Static files (must be last to avoid catching API routes)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "out")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 AgenticMart — PayMind Dashboard starting at http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
