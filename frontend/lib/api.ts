/**
 * PayMind API Client
 * Connects to the FastAPI backend on port 8000
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const WS_BASE = API_BASE.replace("http", "ws");

export interface SessionState {
  session_id: string;
  buyer_id: string;
  cart: {
    items: CartItem[];
    item_count: number;
    total: number;
    total_display: string;
  };
  session_spent: number;
  session_spent_display: string;
  session_cap: number;
  session_cap_display: string;
  session_remaining: number;
  session_remaining_display: string;
  spend_pct: number;
  upsell: {
    offered: number;
    accepted: number;
    acceptance_rate: number;
    acceptance_rate_display: string;
  };
  mandates: MandateChain[];
  current_mandate: MandateChain | null;
  orders: Order[];
}

export interface CartItem {
  product_id: string;
  name: string;
  price: number;
  quantity: number;
  subtotal: number;
}

export interface MandateChain {
  id: string;
  intent?: { raw_request: string; parsed_intent: string; buyer_id: string };
  cart?: { items: CartItem[]; total_amount: number };
  payment?: { approved: boolean; approval_type?: string; block_reasons?: unknown[] };
  completed_at?: number;
  razorpay_order_id?: string;
}

export interface Order {
  razorpay_order_id: string;
  amount: number;
  amount_display: string;
  currency: string;
  status: string;
  receipt: string;
}

export interface AuditEvent {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  reason: string;
  mandate_ref?: string;
  amount?: number;
  rule_outcome: string;
}

export interface RiskScore {
  score: number;
  level: "low" | "medium" | "high" | "critical";
  color: string;
  factors: { name: string; score: number; detail: string }[];
  recommendation: string;
  timestamp: number;
  category_breakdown: { category: string; risk_weight: number; item_count: number; total_amount: number }[];
}

export interface Persona {
  name: string;
  goal: string;
  budget: number;
  style: string;
  emoji: string;
  description: string;
}

// ── REST API calls ────────────────────────────────────────────────

export async function sendChat(message: string): Promise<{ response: string; session: SessionState }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error(`Chat error: ${res.status}`);
  return res.json();
}

export async function getSession(): Promise<SessionState> {
  const res = await fetch(`${API_BASE}/api/session`);
  if (!res.ok) throw new Error(`Session error: ${res.status}`);
  return res.json();
}

export async function resetSession(): Promise<{ message: string; session: SessionState }> {
  const res = await fetch(`${API_BASE}/api/session/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`Reset error: ${res.status}`);
  return res.json();
}

export async function getAuditLog(limit = 50): Promise<{ events: AuditEvent[]; count: number }> {
  const res = await fetch(`${API_BASE}/api/audit?limit=${limit}`);
  if (!res.ok) throw new Error(`Audit error: ${res.status}`);
  return res.json();
}

export async function getRiskScore(): Promise<RiskScore> {
  const res = await fetch(`${API_BASE}/api/risk-score`);
  if (!res.ok) throw new Error(`Risk error: ${res.status}`);
  return res.json();
}

export async function getMandateReport() {
  const res = await fetch(`${API_BASE}/api/mandate-report`);
  if (!res.ok) throw new Error(`Report error: ${res.status}`);
  return res.json();
}

export async function getPersonas(): Promise<{ personas: Record<string, Persona> }> {
  const res = await fetch(`${API_BASE}/api/personas`);
  if (!res.ok) throw new Error(`Personas error: ${res.status}`);
  return res.json();
}

export async function startAIBuyer(persona: string): Promise<{ message: string; persona: Persona; status: string }> {
  const res = await fetch(`${API_BASE}/api/ai-buyer/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ persona }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Start error: ${res.status}`);
  }
  return res.json();
}

export async function getAIBuyerStatus() {
  const res = await fetch(`${API_BASE}/api/ai-buyer/status`);
  if (!res.ok) throw new Error(`Status error: ${res.status}`);
  return res.json();
}

// ── WebSocket ─────────────────────────────────────────────────────

export function createWebSocket(onMessage: (event: unknown) => void): WebSocket | null {
  if (typeof window === "undefined") return null;

  const wsUrl = `${WS_BASE}/ws`;
  let ws: WebSocket;

  try {
    ws = new WebSocket(wsUrl);
  } catch {
    console.warn("WebSocket not available");
    return null;
  }

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      onMessage(data);
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = (err) => {
    console.warn("WebSocket error:", err);
  };

  // Keepalive ping every 20s
  const ping = setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
      ws.send("ping");
    } else {
      clearInterval(ping);
    }
  }, 20000);

  return ws;
}

// ── AP2 Protocol ──────────────────────────────────────────────────

export interface AP2TraceStep {
  phase: string;
  status: string;
  started_at: number | null;
  completed_at: number | null;
  duration_ms: number | null;
  participant: string | null;
  detail: string | null;
  hash_ref: string | null;
  label: string;
  icon: string;
  description: string;
  failure_reason: string | null;
  recovery_action: string | null;
}

export interface AP2Trace {
  trace_id: string;
  buyer_agent: string;
  merchant_agent: string;
  started_at: number;
  completed_at: number | null;
  status: string;
  total_duration_ms: number;
  razorpay_order_id: string | null;
  steps: AP2TraceStep[];
  phase_count: number;
  completed_phases: number;
}

export async function getProtocolTrace(): Promise<{
  current_trace: AP2Trace | null;
  all_traces: AP2Trace[];
  trace_count: number;
}> {
  const res = await fetch(`${API_BASE}/api/protocol/trace`);
  if (!res.ok) throw new Error(`Protocol error: ${res.status}`);
  return res.json();
}

// ── Agent-Readable Catalog ────────────────────────────────────────

export async function getAgentCatalog(): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/catalog/agent-readable`);
  if (!res.ok) throw new Error(`Catalog error: ${res.status}`);
  return res.json();
}

// ── Revenue Metrics ───────────────────────────────────────────────

export interface RevenueMetrics {
  total_revenue: number;
  total_revenue_display: string;
  order_count: number;
  ai_revenue: number;
  ai_revenue_display: string;
  human_revenue: number;
  human_revenue_display: string;
  ai_revenue_pct: number;
  campaign_savings: number;
  campaign_savings_display: string;
  campaign_count: number;
  upsell_offered: number;
  upsell_accepted: number;
  upsell_rate: string;
  blocked_attempts: number;
  overrides: number;
  protocol_traces: number;
}

export async function getRevenueMetrics(): Promise<RevenueMetrics> {
  const res = await fetch(`${API_BASE}/api/revenue/metrics`);
  if (!res.ok) throw new Error(`Revenue error: ${res.status}`);
  return res.json();
}
