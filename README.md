<p align="center">
  <img src="https://img.shields.io/badge/Razorpay-Buildathon_2026-blue?style=for-the-badge&logo=razorpay&logoColor=white" />
  <img src="https://img.shields.io/badge/Track-AI_Growth_&_Agentic_Commerce-blueviolet?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Protocols-AP2_%7C_x402_%7C_ACP_%7C_MPP-teal?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Crypto-ECDSA_P256-orange?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Stack-FastAPI_%7C_Next.js_16_%7C_Gemini-ff6b6b?style=for-the-badge" />
</p>

<h1 align="center">🧠 PayMind</h1>

<p align="center">
  <strong>When AI agents spend real money, who's watching?</strong><br/>
  PayMind is the governance infrastructure between autonomous AI buyers and payment rails.<br/>
  Every transaction: <em>explainable, bounded, auditable, and recoverable</em>.
</p>

<p align="center">
  <code>Gemini 3.6 Flash</code> · <code>Razorpay Test Mode</code> · <code>AP2 ECDSA Mandates</code> · <code>x402 HTTP 402</code> · <code>ACP Checkout</code> · <code>MPP Sessions</code> · <code>Next.js 16</code> · <code>FastAPI</code>
</p>

---

## ⚡ What Makes This Different

> PayMind brings together all four major agentic payment protocols — AP2, x402, ACP, and MPP — with cryptographic authorization, policy enforcement, failure recovery, and a complete audit trail.

| **Dimension**            | **PayMind**                                                                                                                      |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **Protocol coverage**    | Implements **AP2 + x402 + ACP + MPP**, covering authorization, checkout, payment execution, and spending sessions.               |
| **AP2 mandate signing**  | Uses **ECDSA P-256 cryptography** with three mandate types — Intent, Cart, and Payment — as signed JSON-LD objects.              |
| **x402**                 | Implements the live **HTTP 402 → payment challenge → payment proof → 200** flow.                                                 |
| **ACP**                  | Implements the checkout lifecycle with **Create, Update, Complete, and Cancel** endpoints using SharedPaymentTokens.             |
| **MPP**                  | Supports **pre-authorized spending sessions** and micropayments within those sessions.                                           |
| **Policy Gate**          | Every transaction passes through **three rules**: session spend cap, category allowlist, and per-item price limit.               |
| **Failure handling**     | Handles failures through **policy blocking → explanation → human override → recovery**, with every step audited.                 |
| **Audit trail**          | Maintains an **immutable SQLite audit log** containing actors, actions, amounts, mandate references, rule outcomes, and reasons. |
| **Revenue intelligence** | Tracks **AI vs. human revenue, upsell acceptance, campaign performance, and AI buyer behavior** through a live dashboard.        |


---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PAYMIND SYSTEM                                     │
│                                                                               │
│  ┌──────────────┐    ┌────────────────────────────────────────────────────┐  │
│  │   HUMAN      │    │              ORCHESTRATOR AGENT                     │  │
│  │   BUYER      │───▶│  Gemini 3.6 Flash · Tool-Use · Session State       │  │
│  │  (Browser)   │    │  ┌──────────┐ ┌──────────┐ ┌──────────┐           │  │
│  └──────────────┘    │  │ search   │ │ add_to   │ │ checkout │  ...tools  │  │
│                       │  │ products │ │  cart    │ │          │           │  │
│  ┌──────────────┐    │  └──────────┘ └──────────┘ └──────────┘           │  │
│  │   AI BUYER   │    └────────────────────┬───────────────────────────────┘  │
│  │   PERSONAS   │                         │                                   │
│  │ GroceryShopr │    ┌────────────────────▼───────────────────────────────┐  │
│  │ BigSpender   │───▶│              PROTOCOL LAYER                         │  │
│  │ BudgetBot    │    │                                                     │  │
│  └──────────────┘    │  ┌─────────────┐  ┌─────────────┐                 │  │
│                       │  │  AP2 ENGINE  │  │  x402 ENGINE │                 │  │
│                       │  │ ECDSA P-256  │  │  HTTP 402   │                 │  │
│                       │  │  Mandates:   │  │  Challenge/ │                 │  │
│                       │  │  Intent      │  │  Pay/Access │                 │  │
│                       │  │  Cart        │  └─────────────┘                 │  │
│                       │  │  Payment     │  ┌─────────────┐                 │  │
│                       │  └─────────────┘  │  ACP ENGINE  │                 │  │
│                       │  ┌─────────────┐  │  Checkout    │                 │  │
│                       │  │  MPP ENGINE  │  │  SharedPmtTk │                 │  │
│                       │  │  Sessions   │  │  4 endpoints │                 │  │
│                       │  │  Micropaymt │  └─────────────┘                 │  │
│                       │  └─────────────┘                                   │  │
│                       └────────────────────┬───────────────────────────────┘  │
│                                            │                                   │
│              ┌─────────────────────────────▼──────────────────┐               │
│              │                  POLICY GATE                     │               │
│              │  Rule 1: Session Spend Cap (₹2,000)             │               │
│              │  Rule 2: Category Allowlist                      │               │
│              │  Rule 3: Per-Item Price Limit (₹1,500)          │               │
│              │  → ALLOWED: proceed to payment                  │               │
│              │  → BLOCKED: prompt override → audit → recover   │               │
│              └─────────────────────────────┬──────────────────┘               │
│                                            │                                   │
│  ┌──────────────┐    ┌────────────────────▼───────────────────────────────┐  │
│  │  RAZORPAY    │◀───│         PAYMENT ORCHESTRATION                       │  │
│  │  TEST MODE   │    │  Create Order → Capture → Settle                    │  │
│  │  Orders API  │    │  PaymentMandate signed + linked to CartMandate      │  │
│  └──────────────┘    └────────────────────┬───────────────────────────────┘  │
│                                            │                                   │
│              ┌─────────────────────────────▼──────────────────┐               │
│              │              AUDIT & INTELLIGENCE               │               │
│              │  SQLite: 7 actors · Hash-linked mandate chain   │               │
│              │  Revenue Dashboard: AI vs Human split           │               │
│              │  Risk Scorer: 0-100 · Real-time                 │               │
│              │  AP2 Protocol Trace: 6-phase visual             │               │
│              │  WebSocket: Live event streaming to dashboard   │               │
│              └────────────────────────────────────────────────┘               │
│                                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    NEXT.JS 16 DASHBOARD                               │    │
│  │  Chat Panel · AI Arena · Revenue · Catalog · Protocols · Audit · Risk│    │
│  └──────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Problem Statement

> **AI Growth & Agentic Commerce** — *Grow the merchant's revenue, and make them sellable to AI buyers.*
>
> Build an agent that grows revenue for a merchant on Razorpay test-mode APIs, or that makes a merchant transactable by an AI buyer end to end.
>
> **The bar**: Every money action explainable, bounded and gated. Show the audit trail and one failure handled gracefully.

---

## 🌍 Why This Problem Matters Right Now

2026 is the year agent-to-agent commerce became real. Four major protocols launched simultaneously:

| Protocol | Who Built It | What It Solves |
|----------|-------------|----------------|
| **AP2** | Google + 60 partners (Adyen, Mastercard, Coinbase, Revolut) | The *trust layer* — cryptographic mandate authorization |
| **x402** | Coinbase | The *execution layer* — HTTP 402-based instant machine payments |
| **ACP** | OpenAI + Stripe | The *checkout layer* — standardized agent-merchant interaction |
| **MPP** | Stripe + Tempo | The *session layer* — pre-authorized spending with streamed micropayments |

**The problem**: Each protocol only solves part of the story. And no one has built the *governance layer* that sits above all of them — the thing that decides **when an agent is allowed to pay**, proves it cryptographically, and creates an immutable record if something goes wrong.

That's what PayMind is.

---

## 🧭 My Approach

### The Insight

Every discussion about agentic commerce focuses on the *rails* (how does the money move?). Nobody was asking the more important question: **who authorized this agent to spend, and can you prove it?**

A Gemini agent that can buy groceries autonomously is impressive. A Gemini agent that can buy groceries autonomously **within a cryptographically-signed policy mandate, with a 6-phase auditable protocol trace, 3-layer policy gate, and automatic recovery from failures** — that's infrastructure.

### Design Principles

1. **Protocol-first, not feature-first** — Build what the protocol race actually needs, not just a chatbot that calls an API
2. **Every action must be explainable** — If you can't show the mandate chain, the payment didn't happen correctly
3. **Failure is a first-class feature** — The policy gate isn't a safety check, it's a demo moment
4. **Merchant growth is measurable** — Revenue split, upsell rates, and campaign savings should be numbers, not claims

---

## 🚀 My Solution

### Layer 1 — Conversational Commerce Engine

A **Gemini 3.6 Flash** agent with 9 tool functions: `search_products`, `add_to_cart`, `remove_from_cart`, `view_cart`, `checkout`, `view_orders`, `get_recommendations`, `apply_campaign`, `get_session_info`. The agent understands natural language, manages full session state, and triggers the entire payment pipeline from a single chat message.

### Layer 2 — Four Real Protocol Implementations

**AP2 (Agent Payments Protocol) — ECDSA-signed JSON-LD Mandates**

Not a state machine. Real cryptography:

```python
# ECDSA P-256 keypair generated per session
private_key = ec.generate_private_key(ec.SECP256R1())

# CartMandate — signed JSON-LD object (Schema.org compatible)
mandate = {
    "@context": ["https://schema.org/", "https://developers.google.com/agent-payments/ap2/context.jsonld"],
    "@type": "PaymentMandate",
    "mandateType": "CartMandate",
    "items": [...],  # each item with @type: OrderItem
    "totalAmount": { "@type": "MonetaryAmount", "value": 6.30, "currency": "INR" },
    "publicKey": "<base64_DER_public_key>",
    # signed payload:
    "signature": "<96-byte ECDSA-P256-SHA256 signature>",
    "signatureAlgorithm": "ECDSA-P256-SHA256",
}
```

Three mandate types per the AP2 spec: `IntentMandate` → `CartMandate` → `PaymentMandate`, forming a cryptographically-linked chain.

**x402 (Coinbase Payment Protocol) — HTTP 402 Flow**

```bash
# Step 1: AI agent requests a premium resource
GET /api/x402/resource/premium-catalog
# → HTTP 402 Payment Required
{
  "x402Version": "1.0",
  "accepts": [{ "scheme": "exact", "network": "razorpay-testmode",
    "maxAmountRequired": "1.00", "paymentToken": "x402_tok_..." }]
}

# Step 2: Agent pays, sends proof in header
GET /api/x402/resource/premium-catalog
X-PAYMENT: {"paymentToken": "x402_tok_...", "orderId": "order_xxx"}
# → HTTP 200 + resource + X-PAYMENT-RESPONSE receipt
```

Demonstrable live in the browser Network tab.

**ACP (OpenAI/Stripe) — 4-Endpoint Checkout Spec**

```
POST   /api/acp/checkout                → Create Checkout + SharedPaymentToken
GET    /api/acp/checkout/{id}           → Get Checkout state
PUT    /api/acp/checkout/{id}           → Update items
DELETE /api/acp/checkout/{id}           → Cancel
POST   /api/acp/checkout/{id}/complete  → Validate SPT + Razorpay settlement
```

SharedPaymentTokens are single-use, time-bound, and amount-restricted — matching the ACP spec exactly.

**MPP (Stripe/Tempo) — Pre-authorized Session + Micropayments**

```json
// Create a ₹500 pre-authorized spending session
POST /api/mpp/session
{ "agentId": "ai_grocery_shopper", "spendingLimit": 50000, "rail": "razorpay" }

// Stream micropayments within the session (no per-transaction overhead)
POST /api/mpp/session/mpp_abc123/pay
{ "amount": 45000, "description": "Basmati Rice 5kg", "productId": "basmati_rice" }

// Close + settle
DELETE /api/mpp/session/mpp_abc123
→ { "settlement": { "totalTransactions": 3, "totalAmount": 49500, "settledVia": "Razorpay test-mode" } }
```

### Layer 3 — 3-Layer Policy Gate

Every checkout — human or AI — passes through:

```
Rule 1: Session Spend Cap        (₹2,000 hard limit)
Rule 2: Category Allowlist       {groceries, snacks, personal_care, electronics}
Rule 3: Per-Item Price Limit     (₹1,500 per item)
         ↓ BLOCKED → prompt human override → log override in PaymentMandate
         ↓ ALLOWED → proceed to Razorpay order creation
```

### Layer 4 — Revenue Intelligence

- **AI Buyer Arena**: 3 autonomous personas (GroceryShopper, BigSpender, BudgetBot) run concurrently, each with their own AP2 trace
- **Revenue Dashboard**: Real-time split of AI-generated vs human-generated revenue
- **Upsell Engine**: TF-IDF similarity scoring across the catalog, triggers before checkout
- **Campaign Orchestrator**: "AI Early Adopter Bonus" (10% off AI buyers), "Bulk Buyer Discount" (₹150 off 4+ items)
- **Risk Scorer**: 0-100 score based on spend velocity, category risk, behavioral signals

### Layer 5 — Audit Infrastructure

Every event across 7 actors (`buyer`, `orchestrator`, `catalog`, `gate`, `razorpay`, `ai_buyer`, `ap2_protocol`) is written to an immutable SQLite audit log with:
- Timestamp (IST-aware)
- Actor + action
- Mandate reference (links events to the cryptographic chain)
- Amount in paise
- Rule outcome (allowed/blocked/n/a)
- Reason (full human-readable explanation)

Streamed live via WebSocket to the dashboard.

---

## 🔮 The AP2 Protocol Trace — 6 Phases, Visualized

```
DISCOVER → NEGOTIATE → INTENT_LOCK → POLICY_GATE → PAYMENT → SETTLEMENT
   🔍           🤝           🔒            🛡️           💳         ✅

Each phase:
  - Timestamp + duration_ms
  - Participant ID
  - ECDSA hash reference (links to signed mandate)
  - Status: pending | active | completed | failed | recovered
```

This strip is always visible at the top of the dashboard, updating in real-time as you chat.

---

## 🛡️ Failure Handling (The Bar — 3 Scenarios, Not 1)

The problem statement asks for *"one failure handled gracefully."* PayMind demonstrates **three**:

| Failure | Trigger | Recovery |
|---------|---------|----------|
| **Spend Cap Exceeded** | BigSpender persona's cart exceeds ₹2,000 | Policy BLOCKS → agent explains → prompts human override → override logged with `approval_type: "human_override"` in PaymentMandate |
| **Category Blocked** | Requesting a non-allowlisted category | Policy BLOCKS at Rule 2 → agent suggests allowed alternatives from catalog |
| **Model Rate Limit** | Gemini API 429/503 | Automatic fallback chain: `gemini-3.6-flash` → `gemini-2.0-flash-lite` → `gemini-1.5-flash`, logged in audit trail |

All three are visible in the AP2 Protocol Trace as `recovered` phases.

---

## 🧩 Agent-Readable Catalog (Schema.org JSON-LD)

```bash
GET /api/catalog/agent-readable
# Response: Content-Type: application/ld+json
{
  "@context": "https://schema.org/",
  "@type": "ItemList",
  "name": "AgenticMart Product Catalog",
  "description": "Agent-optimized catalog. Supports AP2, x402, ACP, MPP protocols.",
  "itemListElement": [
    {
      "@type": "Product",
      "name": "Premium Basmati Rice 5kg",
      "offers": {
        "@type": "Offer",
        "price": "450.00",
        "priceCurrency": "INR",
        "availability": "InStock"
      }
    }
    // ...
  ]
}
```

Any AI agent on the internet can discover and transact with AgenticMart by reading this endpoint. That's the whole point.

---

## 📊 API Reference

### Core Commerce
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Natural language shopping — triggers full AP2 trace |
| `GET`  | `/api/session` | Current session state: cart, mandates, spend |
| `POST` | `/api/session/reset` | Reset session |

### AP2 Protocol
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/protocol/trace` | Live AP2 6-phase trace |
| `GET`  | `/api/ap2/mandates` | All ECDSA-signed mandates for session |
| `POST` | `/api/ap2/mandate/verify` | Verify a mandate's signature |

### x402 Protocol
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/x402/resource/{key}` | → 402 (no payment) or 200 (with X-PAYMENT header) |
| `POST` | `/api/x402/pay` | Submit payment proof, receive receipt |
| `GET`  | `/api/x402/status` | Pending challenges + completed receipts |

### ACP Protocol
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/acp/checkout` | Create Checkout + SharedPaymentToken |
| `GET`  | `/api/acp/checkout/{id}` | Get Checkout |
| `PUT`  | `/api/acp/checkout/{id}` | Update Checkout |
| `DELETE` | `/api/acp/checkout/{id}` | Cancel Checkout |
| `POST` | `/api/acp/checkout/{id}/complete` | Complete + validate SPT |

### MPP Protocol
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/mpp/session` | Create pre-authorized spending session |
| `GET`  | `/api/mpp/session/{id}` | Get session + micropayment stream |
| `POST` | `/api/mpp/session/{id}/pay` | Stream a micropayment |
| `DELETE` | `/api/mpp/session/{id}` | Close + settle |

### Intelligence
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/protocols` | Live status of all 4 protocols |
| `GET`  | `/api/revenue/metrics` | AI vs human revenue split |
| `GET`  | `/api/audit` | Audit log (all 7 actors) |
| `GET`  | `/api/risk-score` | Real-time 0-100 risk score |
| `GET`  | `/api/mandate-report` | Full mandate compliance report |
| `GET`  | `/api/catalog/agent-readable` | Schema.org JSON-LD catalog |

---

## 🏃 Quick Start

```bash
git clone <repo>
cd RazorpayBuildathon

# Backend
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt

# .env
GEMINI_API_KEY=your_key
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_secret

# Frontend
cd frontend && npm install && npm run build && cd ..

# Run
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** and start shopping 🛒

---

## 🧠 Technical Decisions Worth Asking About

**Why ECDSA P-256 for AP2 mandates?**
The AP2 spec explicitly uses ECDSA with the NIST P-256 curve (secp256r1) — the same curve as HTTPS certificates and Apple Pay. It's a hardware-friendly curve with wide support. A recruiter who knows cryptography will recognize this immediately.

**Why x402 with Razorpay instead of stablecoins?**
x402 is payment-rail agnostic at the protocol level. The 402 challenge/response mechanism is identical whether you settle in USDC on Base or INR via Razorpay. Using Razorpay test-mode makes the demo work without requiring a funded crypto wallet — and demonstrates the protocol is the interesting part, not the rail.

**Why implement all 4 protocols?**
Because the protocol race is the actual thesis of the hackathon track. ACP, AP2, x402, and MPP are genuinely complementary — they operate at different layers (checkout, authorization, execution, session). A real agentic commerce infrastructure uses all four. PayMind is the only submission that demonstrates this.

**Why SQLite?**
Zero-dependency, file-based, instantly inspectable. The mandate chain is in `data/agentic_commerce.db` — you can open it with DB Browser for SQLite during the demo and show the raw rows. That's better than any dashboard.

---

## 🧩 What I'd Build Next

1. **Real ECDSA key registry** — A hosted key server where merchants publish their AP2 public keys (like DKIM for email, but for payments)
2. **Cross-merchant AP2 federation** — One IntentMandate that works across multiple merchants
3. **x402 streaming** — Micropayments per API call, not per resource (true MPP-style streaming over x402)
4. **On-chain mandate anchoring** — Hash the PaymentMandate and anchor it to a public blockchain for tamper-proof provenance
5. **Agent identity layer** — DID-based agent identities so merchants can distinguish between trusted and untrusted buyer agents

---

## 👤 About This Project

Built for **Razorpay Buildathon 2026** · Track: AI Growth & Agentic Commerce

This project is a ground-up implementation of the emerging agentic commerce infrastructure stack. Every component — the ECDSA mandate engine, the x402 flow, the ACP checkout API, the MPP session model — was built from reading the actual protocol specifications, not from tutorials.

The goal was to answer a question the hackathon didn't explicitly ask: *"If AI agents are going to spend billions of dollars autonomously, what does trustworthy, auditable, recoverable agent commerce infrastructure actually look like?"*

PayMind is that answer.
