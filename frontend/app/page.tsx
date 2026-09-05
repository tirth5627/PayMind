"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  getSession,
  getAuditLog,
  getRiskScore,
  getPersonas,
  resetSession,
  createWebSocket,
  SessionState,
  AuditEvent,
  RiskScore,
  Persona,
} from "@/lib/api";
import ChatPanel from "./components/ChatPanel";
import MandateVisualizer from "./components/MandateVisualizer";
import RiskMeter from "./components/RiskMeter";
import AuditLog from "./components/AuditLog";
import AIBuyerArena from "./components/AIBuyerArena";
import SessionMetrics from "./components/SessionMetrics";
import ProtocolTrace from "./components/ProtocolTrace";
import AgentCatalog from "./components/AgentCatalog";
import RevenuePanel from "./components/RevenuePanel";
import ProtocolHub from "./components/ProtocolHub";
import {
  RotateCcw, Wifi, WifiOff, Brain, FileBarChart2, Activity,
  TrendingUp, Globe, Layers, Network,
} from "lucide-react";

type TabId = "arena" | "audit" | "risk" | "revenue" | "catalog" | "protocols";

export default function Home() {
  const [session, setSession] = useState<SessionState | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [personas, setPersonas] = useState<Record<string, Persona>>({});
  const [wsConnected, setWsConnected] = useState(false);
  const [activeTab, setActiveTab] = useState<TabId>("arena");
  const [isResetting, setIsResetting] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadAll = useCallback(async () => {
    try {
      const [s, a, r] = await Promise.all([getSession(), getAuditLog(60), getRiskScore()]);
      setSession(s);
      setAuditEvents(a.events);
      setRiskScore(r);
    } catch {
      // Backend might not be running yet
    }
  }, []);

  useEffect(() => {
    getPersonas()
      .then((p) => setPersonas(p.personas))
      .catch(() => {});

    loadAll();
    pollRef.current = setInterval(loadAll, 3000);

    const ws = createWebSocket((event: unknown) => {
      const data = event as { type: string; session?: SessionState };
      if (!data?.type) return;

      if (data.type === "connected") {
        setWsConnected(true);
      } else if (data.type === "session_update" && data.session) {
        setSession(data.session);
      } else if (
        data.type === "chat_message" ||
        data.type === "ai_buyer_message" ||
        data.type === "session_reset"
      ) {
        loadAll();
      }
    });

    if (ws) {
      wsRef.current = ws;
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
    }

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadAll]);

  const handleSessionUpdate = useCallback((s: SessionState) => {
    setSession(s);
    Promise.all([getAuditLog(60), getRiskScore()])
      .then(([a, r]) => {
        setAuditEvents(a.events);
        setRiskScore(r);
      })
      .catch(() => {});
  }, []);

  const handleReset = async () => {
    setIsResetting(true);
    try {
      const result = await resetSession();
      setSession(result.session);
      setAuditEvents([]);
      setRiskScore(null);
    } catch {
      // ignore
    } finally {
      setIsResetting(false);
    }
  };

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: "arena", label: "AI Arena", icon: Brain },
    { id: "revenue", label: "Revenue", icon: TrendingUp },
    { id: "catalog", label: "Catalog", icon: Globe },
    { id: "protocols", label: "Protocols", icon: Network },
    { id: "audit", label: "Audit", icon: FileBarChart2 },
    { id: "risk", label: "Risk", icon: Activity },
  ];

  const currentMandate = session?.current_mandate || null;

  return (
    <div className="min-h-screen grid-bg flex flex-col">
      {/* ── HEADER ── */}
      <header className="sticky top-0 z-50 glass-strong border-b border-[rgba(255,255,255,0.05)]">
        <div className="max-w-[1600px] mx-auto px-6 h-16 flex items-center gap-6">
          {/* Logo */}
          <motion.div
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-2.5 flex-shrink-0"
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600 to-teal-500 flex items-center justify-center text-lg glow-purple">
              🧠
            </div>
            <div>
              <div className="font-bold text-white leading-none text-sm">PayMind</div>
              <div className="text-[9px] text-[#6c5ce7] font-semibold tracking-[0.2em]">
                AI PAYMENT GOVERNANCE
              </div>
            </div>
          </motion.div>

          {/* Metrics bar */}
          {session && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1 hidden sm:flex items-center gap-5 justify-center"
            >
              {/* Spend bar */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[#5a5a80] uppercase tracking-wider">Spend</span>
                <div className="w-28 h-1.5 rounded-full bg-[#12121e] overflow-hidden">
                  <motion.div
                    animate={{ width: `${session.spend_pct}%` }}
                    className="h-full rounded-full"
                    style={{
                      background:
                        session.spend_pct < 50
                          ? "#00b894"
                          : session.spend_pct < 80
                          ? "#f39c12"
                          : "#d63031",
                    }}
                  />
                </div>
                <span className="text-[10px] font-mono text-white">
                  {session.session_spent_display}
                </span>
              </div>

              <div className="w-px h-4 bg-[rgba(255,255,255,0.08)]" />

              <div className="text-[10px] text-[#5a5a80]">
                Cart: <span className="text-white font-semibold">{session.cart.item_count}</span>
              </div>
              <div className="text-[10px] text-[#5a5a80]">
                Orders: <span className="text-[#fdcb6e] font-semibold">{session.orders.length}</span>
              </div>

              {riskScore && (
                <div
                  className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                  style={{ color: riskScore.color, background: `${riskScore.color}22` }}
                >
                  Risk: {riskScore.score.toFixed(0)}
                </div>
              )}
            </motion.div>
          )}

          {/* Right actions */}
          <div className="flex items-center gap-3 ml-auto">
            <div
              className={`flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full ${
                wsConnected
                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  : "bg-[#12121e] text-[#5a5a80] border border-[rgba(255,255,255,0.05)]"
              }`}
            >
              {wsConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
              <span>{wsConnected ? "LIVE" : "offline"}</span>
            </div>

            <motion.button
              id="btn-reset"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleReset}
              disabled={isResetting}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#12121e] border border-[rgba(255,255,255,0.08)] text-[#a0a0c0] hover:text-white hover:border-[rgba(108,92,231,0.3)] text-xs transition-all disabled:opacity-50"
            >
              <RotateCcw size={11} className={isResetting ? "animate-spin" : ""} />
              Reset
            </motion.button>
          </div>
        </div>
      </header>

      {/* ── AP2 PROTOCOL TRACE (always visible strip) ── */}
      <div className="glass-strong border-b border-[rgba(255,255,255,0.05)]">
        <div className="max-w-[1600px] mx-auto">
          <div className="flex items-center gap-2 px-6 pt-2">
            <Layers size={10} className="text-[#6c5ce7]" />
            <span className="text-[9px] text-[#6c5ce7] font-semibold tracking-widest">AP2 PROTOCOL TRACE</span>
          </div>
          <ProtocolTrace />
        </div>
      </div>

      {/* ── MAIN LAYOUT (2-column) ── */}
      <main className="flex-1 max-w-[1600px] mx-auto w-full p-6 lg:p-8 grid grid-cols-1 lg:grid-cols-[1fr_420px] gap-8">

        {/* ── LEFT: Chat ── */}
        <div className="glass rounded-3xl overflow-hidden flex flex-col min-h-[600px] lg:min-h-0">
          <div className="px-6 py-4 border-b border-[rgba(255,255,255,0.05)] flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse-glow" />
            <h2 className="text-sm font-semibold text-white">Shopping Assistant</h2>
            <span className="ml-auto text-[10px] text-[#a0a0c0] bg-[#12121e] px-2.5 py-0.5 rounded-full border border-[rgba(255,255,255,0.05)]">
              Gemini · Tool-Use
            </span>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel onSessionUpdate={handleSessionUpdate} />
          </div>
        </div>

        {/* ── RIGHT: Panels ── */}
        <div className="space-y-6">
          {/* Session metrics */}
          <SessionMetrics session={session} />

          {/* Mandate chain */}
          <div className="glass rounded-3xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-full bg-teal-500" />
              <h2 className="text-sm font-semibold text-white">Mandate Chain</h2>
              <span className="ml-auto text-[9px] text-teal-500 font-semibold tracking-[0.15em]">AP2 PROTOCOL</span>
            </div>
            <MandateVisualizer chain={currentMandate} />
          </div>

          {/* Order history */}
          {session && session.orders.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="glass rounded-3xl p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <div className="w-2 h-2 rounded-full bg-yellow-400" />
                <h2 className="text-sm font-semibold text-white">Orders</h2>
              </div>
              <div className="space-y-3">
                {session.orders.map((order) => (
                  <div
                    key={order.razorpay_order_id}
                    className="rounded-xl bg-[#0d0d14] border border-[rgba(253,203,110,0.15)] p-3"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-[#fdcb6e]">{order.amount_display}</span>
                      <span className="text-[10px] text-emerald-400 font-semibold uppercase">
                        {order.status}
                      </span>
                    </div>
                    <p className="text-[10px] font-mono text-[#5a5a80] truncate">
                      {order.razorpay_order_id}
                    </p>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* ── Tabbed Panel (Arena / Revenue / Catalog / Audit / Risk) ── */}
          <div className="glass rounded-3xl overflow-hidden flex flex-col">
            <div className="flex border-b border-[rgba(255,255,255,0.05)] px-1 pt-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  id={`tab-${tab.id}`}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex-1 py-3 text-[10px] font-semibold flex items-center justify-center gap-1.5 transition-all relative rounded-t-xl ${
                    activeTab === tab.id
                      ? "text-white bg-[rgba(255,255,255,0.03)]"
                      : "text-[#5a5a80] hover:text-[#a0a0c0] hover:bg-[rgba(255,255,255,0.01)]"
                  }`}
                >
                  <tab.icon size={11} />
                  {tab.label}
                  {activeTab === tab.id && (
                    <motion.div
                      layoutId="tab-indicator"
                      className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 to-teal-500"
                    />
                  )}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-5 min-h-0" style={{ maxHeight: "500px" }}>
              <AnimatePresence mode="wait">
                {activeTab === "arena" && (
                  <motion.div key={`arena-${session?.session_id || 'initial'}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <AIBuyerArena personas={personas} />
                  </motion.div>
                )}
                {activeTab === "revenue" && (
                  <motion.div key="revenue" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <RevenuePanel />
                  </motion.div>
                )}
                {activeTab === "catalog" && (
                  <motion.div key="catalog" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <AgentCatalog />
                  </motion.div>
                )}
                {activeTab === "audit" && (
                  <motion.div key="audit" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs text-[#5a5a80]">{auditEvents.length} events</span>
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    </div>
                    <AuditLog events={auditEvents} />
                  </motion.div>
                )}
                {activeTab === "risk" && (
                  <motion.div key="risk" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <RiskMeter riskScore={riskScore} />
                  </motion.div>
                )}
                {activeTab === "protocols" && (
                  <motion.div key="protocols" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.2 }}>
                    <ProtocolHub />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </main>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[rgba(255,255,255,0.05)] py-4 px-6 bg-[#050508]/80 backdrop-blur-md">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between text-[10px] text-[#5a5a80]">
          <span>PayMind · AgenticMart · Razorpay Buildathon 2026</span>
          <div className="flex items-center gap-3">
            <span>Backend: localhost:8000</span>
            <span className={wsConnected ? "text-emerald-600" : "text-red-900"}>
              WS: {wsConnected ? "connected" : "disconnected"}
            </span>
            <span>Session: {session?.session_id || "—"}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
