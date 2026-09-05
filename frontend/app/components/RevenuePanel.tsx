"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { getRevenueMetrics, RevenueMetrics } from "@/lib/api";
import { TrendingUp, Bot, User, Zap, ShieldCheck, Gift } from "lucide-react";

function AnimatedCounter({ value, prefix = "" }: { value: number; prefix?: string }) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    if (value === 0) { setDisplay(0); return; }
    const duration = 800;
    const steps = 30;
    const increment = value / steps;
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= value) {
        setDisplay(value);
        clearInterval(timer);
      } else {
        setDisplay(current);
      }
    }, duration / steps);
    return () => clearInterval(timer);
  }, [value]);

  return (
    <span className="font-mono font-bold">
      {prefix}{(display / 100).toFixed(2)}
    </span>
  );
}

export default function RevenuePanel() {
  const [metrics, setMetrics] = useState<RevenueMetrics | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getRevenueMetrics();
      setMetrics(data);
    } catch {
      // Backend not ready
    }
  }, []);

  useEffect(() => {
    load();
    const poll = setInterval(load, 3000);
    return () => clearInterval(poll);
  }, [load]);

  if (!metrics) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <TrendingUp size={20} className="text-[#5a5a80] mb-2" />
        <p className="text-xs text-[#5a5a80]">Revenue metrics load after first transaction</p>
      </div>
    );
  }

  const aiPct = metrics.ai_revenue_pct;
  const humanPct = 100 - aiPct;

  return (
    <div className="space-y-5">
      {/* Hero Revenue Counter */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="rounded-xl bg-gradient-to-br from-[rgba(108,92,231,0.1)] to-[rgba(0,206,201,0.05)] border border-[rgba(108,92,231,0.2)] p-4 text-center"
      >
        <div className="text-[10px] text-[#a0a0c0] uppercase tracking-widest mb-1">Total Revenue</div>
        <div className="text-2xl text-white">
          <AnimatedCounter value={metrics.total_revenue} prefix="₹" />
        </div>
        <div className="text-[10px] text-[#5a5a80] mt-1">
          {metrics.order_count} order{metrics.order_count !== 1 ? "s" : ""} · {metrics.protocol_traces} AP2 trace{metrics.protocol_traces !== 1 ? "s" : ""}
        </div>
      </motion.div>

      {/* AI vs Human Revenue Split */}
      {metrics.total_revenue > 0 && (
        <div className="space-y-2">
          <div className="text-[10px] text-[#a0a0c0] uppercase tracking-wider font-semibold">Revenue Source</div>

          {/* CSS Donut Chart */}
          <div className="flex items-center gap-4">
            <div className="relative w-16 h-16 flex-shrink-0">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.5" fill="none" stroke="#12121e" strokeWidth="3" />
                <motion.circle
                  cx="18" cy="18" r="15.5" fill="none"
                  stroke="#6c5ce7" strokeWidth="3"
                  strokeDasharray={`${aiPct} ${100 - aiPct}`}
                  strokeLinecap="round"
                  initial={{ strokeDasharray: "0 100" }}
                  animate={{ strokeDasharray: `${aiPct} ${100 - aiPct}` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
                <motion.circle
                  cx="18" cy="18" r="15.5" fill="none"
                  stroke="#00cec9" strokeWidth="3"
                  strokeDasharray={`${humanPct} ${100 - humanPct}`}
                  strokeDashoffset={`-${aiPct}`}
                  strokeLinecap="round"
                  initial={{ strokeDasharray: "0 100" }}
                  animate={{ strokeDasharray: `${humanPct} ${100 - humanPct}` }}
                  transition={{ duration: 1, ease: "easeOut", delay: 0.3 }}
                />
              </svg>
            </div>
            <div className="flex-1 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Bot size={10} className="text-[#6c5ce7]" />
                  <span className="text-[10px] text-[#a0a0c0]">AI Agents</span>
                </div>
                <span className="text-[10px] font-mono font-bold text-[#6c5ce7]">
                  {metrics.ai_revenue_display} ({aiPct.toFixed(0)}%)
                </span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <User size={10} className="text-[#00cec9]" />
                  <span className="text-[10px] text-[#a0a0c0]">Human</span>
                </div>
                <span className="text-[10px] font-mono font-bold text-[#00cec9]">
                  {metrics.human_revenue_display} ({humanPct.toFixed(0)}%)
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Growth Metrics Grid */}
      <div className="grid grid-cols-2 gap-2">
        {[
          {
            icon: Gift, label: "Campaigns", value: metrics.campaign_count.toString(),
            sub: `Saved ${metrics.campaign_savings_display}`, color: "#fdcb6e",
          },
          {
            icon: Zap, label: "Upsell Rate", value: metrics.upsell_rate,
            sub: `${metrics.upsell_accepted}/${metrics.upsell_offered} accepted`, color: "#fd79a8",
          },
          {
            icon: ShieldCheck, label: "Policy Blocks", value: metrics.blocked_attempts.toString(),
            sub: `${metrics.overrides} overridden`, color: "#e17055",
          },
          {
            icon: TrendingUp, label: "AP2 Traces", value: metrics.protocol_traces.toString(),
            sub: "protocol runs", color: "#6c5ce7",
          },
        ].map((m, i) => (
          <motion.div
            key={m.label}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-lg bg-[#0d0d14] border border-[rgba(255,255,255,0.04)] p-3"
          >
            <m.icon size={12} style={{ color: m.color }} className="mb-1.5" />
            <div className="text-sm font-bold text-white">{m.value}</div>
            <div className="text-[9px] text-[#5a5a80] uppercase tracking-wider">{m.label}</div>
            <div className="text-[9px] text-[#a0a0c0] mt-0.5">{m.sub}</div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
