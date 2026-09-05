"use client";

import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Shield, Zap, ShoppingCart, Layers, CheckCircle, Clock, XCircle, ExternalLink, Copy, ChevronDown, ChevronUp, Play, RefreshCw } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ProtocolStatus {
  name: string;
  version: string;
  developer: string;
  layer: string;
  description: string;
  status: string;
  [key: string]: unknown;
}

const PROTOCOL_META: Record<string, { icon: React.ElementType; color: string; glow: string; bg: string; border: string }> = {
  ap2: {
    icon: Shield,
    color: "#6c5ce7",
    glow: "rgba(108,92,231,0.3)",
    bg: "rgba(108,92,231,0.06)",
    border: "rgba(108,92,231,0.2)",
  },
  x402: {
    icon: Zap,
    color: "#00cec9",
    glow: "rgba(0,206,201,0.3)",
    bg: "rgba(0,206,201,0.06)",
    border: "rgba(0,206,201,0.2)",
  },
  acp: {
    icon: ShoppingCart,
    color: "#fdcb6e",
    glow: "rgba(253,203,110,0.3)",
    bg: "rgba(253,203,110,0.06)",
    border: "rgba(253,203,110,0.2)",
  },
  mpp: {
    icon: Layers,
    color: "#00b894",
    glow: "rgba(0,184,148,0.3)",
    bg: "rgba(0,184,148,0.06)",
    border: "rgba(0,184,148,0.2)",
  },
};

const LAYER_ORDER = ["Authorization & Trust", "Execution & Settlement", "Checkout & Merchant Integration", "Session & Micropayments"];

// Quick demo actions per protocol
const DEMO_ACTIONS: Record<string, { label: string; action: () => Promise<unknown> }[]> = {};

function ProtocolCard({ protocolKey, data }: { protocolKey: string; data: ProtocolStatus }) {
  const [expanded, setExpanded] = useState(false);
  const [demoResult, setDemoResult] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const meta = PROTOCOL_META[protocolKey];
  const Icon = meta.icon;

  const runDemo = useCallback(async () => {
    setLoading(true);
    setDemoResult(null);
    try {
      let result: unknown;
      if (protocolKey === "ap2") {
        const res = await fetch(`${API}/api/ap2/mandates`);
        result = await res.json();
      } else if (protocolKey === "x402") {
        const res = await fetch(`${API}/api/x402/resource/premium-catalog`);
        result = await res.json();
      } else if (protocolKey === "acp") {
        const res = await fetch(`${API}/api/acp/checkouts`);
        result = await res.json();
      } else if (protocolKey === "mpp") {
        const res = await fetch(`${API}/api/mpp/sessions`);
        result = await res.json();
      }
      setDemoResult(result);
    } catch (e) {
      setDemoResult({ error: String(e) });
    } finally {
      setLoading(false);
    }
  }, [protocolKey]);

  const copyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(demoResult, null, 2));
  };

  // Build stat pills from protocol-specific keys
  const stats: { label: string; value: string | number }[] = [];
  if (protocolKey === "ap2") {
    stats.push({ label: "Mandates", value: (data.mandateCount as number) ?? 0 });
    stats.push({ label: "Algorithm", value: "ECDSA-P256" });
  } else if (protocolKey === "x402") {
    stats.push({ label: "Pending", value: (data.pendingChallenges as number) ?? 0 });
    stats.push({ label: "Receipts", value: (data.completedReceipts as number) ?? 0 });
  } else if (protocolKey === "acp") {
    stats.push({ label: "Active", value: (data.activeCheckouts as number) ?? 0 });
    stats.push({ label: "Completed", value: (data.completedCheckouts as number) ?? 0 });
  } else if (protocolKey === "mpp") {
    stats.push({ label: "Sessions", value: (data.activeSessions as number) ?? 0 });
    stats.push({ label: "Payments", value: (data.totalMicropayments as number) ?? 0 });
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border p-4 flex flex-col gap-3 transition-all"
      style={{ background: meta.bg, borderColor: meta.border }}
    >
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: `${meta.color}20`, boxShadow: `0 0 12px ${meta.glow}` }}
        >
          <Icon size={16} style={{ color: meta.color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-xs font-bold text-white">{data.name}</h3>
            <span
              className="text-[9px] font-mono px-1.5 py-0.5 rounded-sm"
              style={{ color: meta.color, background: `${meta.color}20` }}
            >
              {data.version}
            </span>
            <span className="ml-auto text-[9px] text-[#00b894] bg-[#00b89420] px-1.5 py-0.5 rounded-full font-semibold">
              ● ACTIVE
            </span>
          </div>
          <p className="text-[9px] text-[#5a5a80] mt-0.5">{data.developer}</p>
        </div>
      </div>

      {/* Layer badge */}
      <div
        className="text-[9px] font-semibold tracking-wider px-2 py-1 rounded-lg w-fit"
        style={{ color: meta.color, background: `${meta.color}15`, border: `1px solid ${meta.border}` }}
      >
        {data.layer.toUpperCase()}
      </div>

      {/* Description */}
      <p className="text-[11px] text-[#a0a0c0] leading-relaxed">{data.description}</p>

      {/* Stats row */}
      <div className="flex gap-2">
        {stats.map((s) => (
          <div key={s.label} className="flex-1 rounded-lg bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] p-2 text-center">
            <div className="text-sm font-bold" style={{ color: meta.color }}>{s.value}</div>
            <div className="text-[9px] text-[#5a5a80] mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={runDemo}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-[10px] font-semibold transition-all"
          style={{
            background: `${meta.color}20`,
            color: meta.color,
            border: `1px solid ${meta.border}`,
          }}
        >
          {loading ? <RefreshCw size={10} className="animate-spin" /> : <Play size={10} />}
          {loading ? "Fetching..." : "Ping API"}
        </motion.button>
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => setExpanded(!expanded)}
          className="px-3 py-2 rounded-xl text-[10px] font-semibold bg-[#12121e] border border-[rgba(255,255,255,0.05)] text-[#a0a0c0] hover:text-white transition-all"
        >
          {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </motion.button>
      </div>

      {/* Endpoints */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="pt-1 space-y-1">
              <p className="text-[9px] text-[#5a5a80] font-semibold tracking-wider mb-1.5">ENDPOINTS</p>
              {(data.endpoints as string[]).map((ep) => (
                <div key={ep} className="font-mono text-[10px] text-[#a0a0c0] bg-[#0d0d14] rounded-lg px-2 py-1.5 border border-[rgba(255,255,255,0.04)]">
                  {ep}
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* API Response */}
      <AnimatePresence>
      {demoResult !== null && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="rounded-xl bg-[#050508] border border-[rgba(255,255,255,0.06)] overflow-hidden">
              <div className="flex items-center justify-between px-3 py-1.5 border-b border-[rgba(255,255,255,0.05)]">
                <span className="text-[9px] text-[#5a5a80] font-mono">API RESPONSE</span>
                <button onClick={copyJson} className="text-[9px] text-[#6c5ce7] hover:text-white flex items-center gap-1 transition-colors">
                  <Copy size={9} /> copy
                </button>
              </div>
              <pre className="text-[9px] font-mono text-[#a0a0c0] p-3 overflow-x-auto max-h-40">
                {JSON.stringify(demoResult as object, null, 2).slice(0, 800)}
                {JSON.stringify(demoResult as object, null, 2).length > 800 ? "\n…" : ""}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// x402 Demo — live 402 flow
function X402Demo() {
  const [step, setStep] = useState<"idle" | "challenged" | "paid">("idle");
  const [challenge, setChallenge] = useState<unknown>(null);
  const [receipt, setReceipt] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);

  const requestResource = async () => {
    setLoading(true);
    setStep("idle");
    try {
      const res = await fetch(`${API}/api/x402/resource/premium-catalog`);
      const data = await res.json();
      setChallenge(data);
      setStep("challenged");
    } catch (e) {
      setChallenge({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  const payAndAccess = async () => {
    if (!challenge || typeof challenge !== "object" || !("paymentToken" in challenge)) return;
    setLoading(true);
    try {
      const token = (challenge as { paymentToken: string }).paymentToken;
      const res = await fetch(`${API}/api/x402/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          paymentToken: token,
          orderId: `demo_order_${Date.now()}`,
          network: "razorpay-testmode",
        }),
      });
      const data = await res.json();
      setReceipt(data);
      setStep("paid");
    } catch (e) {
      setReceipt({ error: String(e) });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-[rgba(0,206,201,0.2)] bg-[rgba(0,206,201,0.04)] p-4 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <Zap size={13} className="text-[#00cec9]" />
        <span className="text-xs font-bold text-white">x402 Live Demo</span>
        <span className="ml-auto text-[9px] text-[#5a5a80]">HTTP 402 → Payment → 200</span>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-4">
        {["Request Resource", "Get 402 Challenge", "Pay & Access"].map((label, i) => {
          const active = (step === "idle" && i === 0) || (step === "challenged" && i === 1) || (step === "paid" && i === 2);
          const done = (step === "challenged" && i === 0) || (step === "paid" && i <= 1);
          return (
            <div key={label} className="flex items-center gap-1">
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold transition-all ${
                  done ? "bg-[#00cec9] text-[#050508]" : active ? "bg-[#00cec920] border border-[#00cec9] text-[#00cec9]" : "bg-[#12121e] text-[#5a5a80] border border-[rgba(255,255,255,0.05)]"
                }`}
              >
                {done ? "✓" : i + 1}
              </div>
              <span className={`text-[9px] ${active ? "text-white" : "text-[#5a5a80]"}`}>{label}</span>
              {i < 2 && <div className="w-4 h-px bg-[rgba(255,255,255,0.1)]" />}
            </div>
          );
        })}
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={requestResource}
          disabled={loading}
          className="flex-1 py-2 rounded-xl text-[10px] font-semibold bg-[rgba(0,206,201,0.15)] text-[#00cec9] border border-[rgba(0,206,201,0.25)] hover:bg-[rgba(0,206,201,0.25)] transition-all"
        >
          {loading && step === "idle" ? "Requesting..." : "1. Request Premium Catalog"}
        </motion.button>
        {step === "challenged" && (
          <motion.button
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={payAndAccess}
            disabled={loading}
            className="flex-1 py-2 rounded-xl text-[10px] font-semibold bg-[rgba(0,184,148,0.2)] text-[#00b894] border border-[rgba(0,184,148,0.3)] hover:bg-[rgba(0,184,148,0.3)] transition-all"
          >
            {loading ? "Paying..." : "2. Pay ₹1 & Access"}
          </motion.button>
        )}
      </div>

      {/* Response */}
      {step !== "idle" && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 rounded-xl bg-[#050508] border border-[rgba(255,255,255,0.06)] overflow-hidden"
        >
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-[rgba(255,255,255,0.05)]">
            <div className="flex items-center gap-2">
              <span
                className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                  step === "challenged" ? "bg-yellow-500/20 text-yellow-400" : "bg-emerald-500/20 text-emerald-400"
                }`}
              >
                HTTP {step === "challenged" ? "402" : "200"}
              </span>
              <span className="text-[9px] text-[#5a5a80] font-mono">
                {step === "challenged" ? "Payment Required" : "OK — Resource Accessed"}
              </span>
            </div>
          </div>
          <pre className="text-[9px] font-mono text-[#a0a0c0] p-3 overflow-x-auto max-h-36">
            {JSON.stringify(step === "challenged" ? challenge : receipt, null, 2).slice(0, 600)}
          </pre>
        </motion.div>
      )}
    </div>
  );
}

// MPP Session Demo
interface MPPSessionState {
  sessionId: string;
  status: string;
  spendingLimitDisplay: string;
  totalSpentDisplay: string;
  remainingDisplay: string;
  utilizationPct: number;
  micropaymentCount: number;
  micropayments: unknown[];
}

function MPPDemo() {
  const [session, setSession] = useState<MPPSessionState | null>(null);
  const [loading, setLoading] = useState(false);

  const createSession = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/mpp/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          agentId: "demo_agent",
          spendingLimit: 50000,  // ₹500
          currency: "INR",
          rail: "razorpay",
          description: "Demo shopping session",
        }),
      });
      setSession(await res.json());
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  const streamPayment = async () => {
    if (!session?.sessionId) return;
    setLoading(true);
    try {
      const sid = session.sessionId;
      const res = await fetch(`${API}/api/mpp/session/${sid}/pay`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          amount: 45000,
          description: "Premium Basmati Rice 5kg",
          productId: "basmati_rice",
        }),
      });
      const payment = await res.json();
      // Refresh session
      const sRes = await fetch(`${API}/api/mpp/session/${sid}`);
      setSession(await sRes.json());
    } catch {
      setSession(null);
    } finally {
      setLoading(false);
    }
  };

  const hasSession = !!session;
  const s = session;

  return (
    <div className="rounded-2xl border border-[rgba(0,184,148,0.2)] bg-[rgba(0,184,148,0.04)] p-4 mt-4">
      <div className="flex items-center gap-2 mb-3">
        <Layers size={13} className="text-[#00b894]" />
        <span className="text-xs font-bold text-white">MPP Session Demo</span>
        <span className="ml-auto text-[9px] text-[#5a5a80]">Pre-authorize → Stream payments</span>
      </div>

      <div className="flex gap-2">
        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={createSession}
          disabled={loading || !!hasSession}
          className="flex-1 py-2 rounded-xl text-[10px] font-semibold bg-[rgba(0,184,148,0.15)] text-[#00b894] border border-[rgba(0,184,148,0.25)] hover:bg-[rgba(0,184,148,0.25)] transition-all disabled:opacity-50"
        >
          Create ₹500 Session
        </motion.button>
        {hasSession && (
          <motion.button
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={streamPayment}
            disabled={loading}
            className="flex-1 py-2 rounded-xl text-[10px] font-semibold bg-[rgba(108,92,231,0.15)] text-[#6c5ce7] border border-[rgba(108,92,231,0.25)] transition-all"
          >
            Stream ₹450 Payment
          </motion.button>
        )}
      </div>

      {s && (
        <motion.div
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-3 space-y-2"
        >
          {hasSession && (
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: "Authorized", value: s.spendingLimitDisplay },
                { label: "Spent", value: s.totalSpentDisplay },
                { label: "Remaining", value: s.remainingDisplay },
              ].map((item) => (
                <div key={item.label} className="rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] p-2 text-center">
                  <div className="text-xs font-bold text-[#00b894]">{item.value}</div>
                  <div className="text-[8px] text-[#5a5a80] mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>
          )}
          {hasSession && (
            <div className="w-full h-1.5 rounded-full bg-[#12121e] overflow-hidden">
              <motion.div
                animate={{ width: `${s.utilizationPct}%` }}
                className="h-full rounded-full bg-gradient-to-r from-[#00b894] to-[#6c5ce7]"
              />
            </div>
          )}
          <div className="text-[9px] text-[#5a5a80] font-mono">
            Session: {s.sessionId} ·{" "}
            Payments: {s.micropaymentCount} streamed
          </div>
        </motion.div>
      )}
    </div>
  );
}

export default function ProtocolHub() {
  const [protocols, setProtocols] = useState<Record<string, ProtocolStatus> | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeDemo, setActiveDemo] = useState<"x402" | "mpp" | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/protocols`);
      const data = await res.json();
      setProtocols(data);
    } catch {
      // Backend might not be ready
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [load]);

  const PROTOCOL_ORDER = ["ap2", "x402", "acp", "mpp"];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white">Agentic Payment Protocols</h2>
          <p className="text-[10px] text-[#5a5a80] mt-0.5">All 4 protocols implemented & active</p>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={load}
          className="p-2 rounded-xl bg-[#12121e] border border-[rgba(255,255,255,0.05)] text-[#5a5a80] hover:text-white transition-all"
        >
          <RefreshCw size={11} />
        </motion.button>
      </div>

      {/* Protocol cards */}
      {loading ? (
        <div className="grid grid-cols-2 gap-3">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="rounded-2xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] p-4 h-48 animate-pulse" />
          ))}
        </div>
      ) : protocols ? (
        <div className="grid grid-cols-2 gap-3">
          {PROTOCOL_ORDER.map((key) =>
            protocols[key] ? (
              <ProtocolCard key={key} protocolKey={key} data={protocols[key]} />
            ) : null
          )}
        </div>
      ) : (
        <div className="text-center py-8 text-[#5a5a80] text-xs">Backend not reachable</div>
      )}

      {/* Live Demos */}
      <div className="rounded-2xl border border-[rgba(255,255,255,0.06)] bg-[#0a0a12] p-4">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-1.5 h-1.5 rounded-full bg-[#00cec9] animate-pulse" />
          <span className="text-xs font-bold text-white">Live Protocol Demos</span>
        </div>
        <div className="flex gap-2 mb-0">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setActiveDemo(activeDemo === "x402" ? null : "x402")}
            className={`flex-1 py-2 rounded-xl text-[10px] font-semibold transition-all ${
              activeDemo === "x402"
                ? "bg-[rgba(0,206,201,0.2)] text-[#00cec9] border border-[rgba(0,206,201,0.3)]"
                : "bg-[#12121e] text-[#5a5a80] border border-[rgba(255,255,255,0.05)] hover:text-white"
            }`}
          >
            ⚡ x402 Flow
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setActiveDemo(activeDemo === "mpp" ? null : "mpp")}
            className={`flex-1 py-2 rounded-xl text-[10px] font-semibold transition-all ${
              activeDemo === "mpp"
                ? "bg-[rgba(0,184,148,0.2)] text-[#00b894] border border-[rgba(0,184,148,0.3)]"
                : "bg-[#12121e] text-[#5a5a80] border border-[rgba(255,255,255,0.05)] hover:text-white"
            }`}
          >
            🔄 MPP Session
          </motion.button>
        </div>
        <AnimatePresence>
          {activeDemo === "x402" && <X402Demo />}
          {activeDemo === "mpp" && <MPPDemo />}
        </AnimatePresence>
      </div>
    </div>
  );
}
