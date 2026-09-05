"use client";

import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { getProtocolTrace, AP2Trace } from "@/lib/api";

const PHASE_COLORS: Record<string, { bg: string; glow: string; border: string }> = {
  DISCOVER: { bg: "from-blue-500 to-cyan-500", glow: "rgba(59,130,246,0.4)", border: "border-blue-500/30" },
  NEGOTIATE: { bg: "from-purple-500 to-pink-500", glow: "rgba(168,85,247,0.4)", border: "border-purple-500/30" },
  INTENT_LOCK: { bg: "from-indigo-500 to-purple-500", glow: "rgba(99,102,241,0.4)", border: "border-indigo-500/30" },
  POLICY_GATE: { bg: "from-amber-500 to-orange-500", glow: "rgba(245,158,11,0.4)", border: "border-amber-500/30" },
  PAYMENT: { bg: "from-emerald-500 to-teal-500", glow: "rgba(16,185,129,0.4)", border: "border-emerald-500/30" },
  SETTLEMENT: { bg: "from-green-400 to-emerald-500", glow: "rgba(52,211,153,0.4)", border: "border-green-500/30" },
};

export default function ProtocolTrace() {
  const [trace, setTrace] = useState<AP2Trace | null>(null);

  const loadTrace = useCallback(async () => {
    try {
      const data = await getProtocolTrace();
      setTrace(data.current_trace);
    } catch {
      // Backend not ready
    }
  }, []);

  useEffect(() => {
    loadTrace();
    const poll = setInterval(loadTrace, 2000);
    return () => clearInterval(poll);
  }, [loadTrace]);

  if (!trace) {
    return (
      <div className="flex items-center gap-3 px-4 py-3">
        {["DISCOVER", "NEGOTIATE", "INTENT_LOCK", "POLICY_GATE", "PAYMENT", "SETTLEMENT"].map((phase, i) => (
          <div key={phase} className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#12121e] border border-[rgba(255,255,255,0.05)] flex items-center justify-center text-[10px] text-[#5a5a80]">
              {i + 1}
            </div>
            {i < 5 && <div className="w-6 h-px bg-[#1a1a2e]" />}
          </div>
        ))}
        <span className="text-[10px] text-[#5a5a80] ml-auto font-mono">AP2 IDLE</span>
      </div>
    );
  }

  return (
    <div className="px-4 py-3">
      {/* Protocol ID + Status */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-purple-500 animate-pulse" />
          <span className="text-[10px] font-mono text-[#6c5ce7]">{trace.trace_id}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-[#a0a0c0]">
            {trace.completed_phases}/{trace.phase_count}
          </span>
          {trace.status === "completed" && (
            <span className="text-[9px] bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 rounded font-semibold">
              SETTLED
            </span>
          )}
          {trace.status === "in_progress" && (
            <span className="text-[9px] bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded font-semibold animate-pulse">
              ACTIVE
            </span>
          )}
        </div>
      </div>

      {/* Phase Pipeline */}
      <div className="flex items-center gap-1.5">
        {trace.steps.map((step, i) => {
          const colors = PHASE_COLORS[step.phase] || PHASE_COLORS.DISCOVER;
          const isCompleted = step.status === "completed" || step.status === "recovered";
          const isActive = step.status === "active";
          const isFailed = step.status === "failed";
          const isRecovered = step.status === "recovered";

          return (
            <div key={step.phase} className="flex items-center gap-1.5 flex-1">
              <motion.div
                initial={{ scale: 0.9, opacity: 0.5 }}
                animate={{
                  scale: isActive ? [1, 1.05, 1] : 1,
                  opacity: isCompleted || isActive ? 1 : 0.4,
                }}
                transition={isActive ? { repeat: Infinity, duration: 1.5 } : { duration: 0.3 }}
                className="relative group"
              >
                <div
                  className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm transition-all ${
                    isCompleted
                      ? `bg-gradient-to-br ${colors.bg} text-white`
                      : isFailed
                      ? "bg-red-500/20 border border-red-500/40 text-red-400"
                      : isActive
                      ? `border-2 ${colors.border} bg-[#12121e] text-white`
                      : "bg-[#12121e] border border-[rgba(255,255,255,0.05)] text-[#5a5a80]"
                  }`}
                  style={isCompleted ? { boxShadow: `0 0 12px ${colors.glow}` } : {}}
                >
                  {step.icon}
                </div>

                {/* Tooltip */}
                <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded-lg bg-[#1a1a2e] border border-[rgba(255,255,255,0.1)] text-[9px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  <div className="font-bold text-white mb-0.5">{step.label}</div>
                  {step.detail && <div className="text-[#a0a0c0]">{step.detail}</div>}
                  {step.duration_ms !== null && (
                    <div className="text-[#6c5ce7] font-mono">{step.duration_ms.toFixed(0)}ms</div>
                  )}
                  {isRecovered && (
                    <div className="text-amber-400 mt-0.5">⚡ {step.recovery_action}</div>
                  )}
                  {step.hash_ref && (
                    <div className="text-[#5a5a80] font-mono mt-0.5">#{step.hash_ref.slice(0, 8)}</div>
                  )}
                </div>
              </motion.div>

              {/* Connector line */}
              {i < trace.steps.length - 1 && (
                <div className="flex-1 h-px relative overflow-hidden">
                  <div className="absolute inset-0 bg-[#1a1a2e]" />
                  {isCompleted && (
                    <motion.div
                      initial={{ width: "0%" }}
                      animate={{ width: "100%" }}
                      transition={{ duration: 0.4, delay: 0.1 }}
                      className={`absolute inset-y-0 left-0 bg-gradient-to-r ${colors.bg}`}
                    />
                  )}
                  {isActive && (
                    <motion.div
                      animate={{ x: ["-100%", "200%"] }}
                      transition={{ repeat: Infinity, duration: 1.5, ease: "linear" }}
                      className={`absolute inset-y-0 w-1/3 bg-gradient-to-r ${colors.bg} opacity-60`}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Timing bar */}
      {trace.total_duration_ms > 0 && (
        <div className="flex items-center justify-between mt-2">
          <span className="text-[9px] text-[#5a5a80] font-mono">
            {trace.buyer_agent} → {trace.merchant_agent}
          </span>
          <span className="text-[9px] text-[#a0a0c0] font-mono">
            {(trace.total_duration_ms / 1000).toFixed(1)}s total
          </span>
        </div>
      )}
    </div>
  );
}
