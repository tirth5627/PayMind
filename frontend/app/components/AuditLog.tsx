"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AuditEvent } from "@/lib/api";
import { clsx } from "clsx";

interface Props {
  events: AuditEvent[];
}

const ACTOR_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  buyer: { color: "#6c5ce7", bg: "rgba(108,92,231,0.15)", label: "BUYER" },
  orchestrator: { color: "#00cec9", bg: "rgba(0,206,201,0.15)", label: "AGENT" },
  razorpay: { color: "#fdcb6e", bg: "rgba(253,203,110,0.15)", label: "RAZORPAY" },
  ai_buyer: { color: "#fd79a8", bg: "rgba(253,121,168,0.15)", label: "AI BUYER" },
  catalog: { color: "#74b9ff", bg: "rgba(116,185,255,0.15)", label: "CATALOG" },
  gate: { color: "#e17055", bg: "rgba(225,112,85,0.15)", label: "POLICY" },
  default: { color: "#a0a0c0", bg: "rgba(160,160,192,0.1)", label: "SYS" },
};

const OUTCOME_CONFIG: Record<string, { color: string; dot: string }> = {
  allowed: { color: "text-emerald-400", dot: "bg-emerald-400" },
  blocked: { color: "text-red-400", dot: "bg-red-400" },
  "n/a": { color: "text-[#5a5a80]", dot: "bg-[#5a5a80]" },
};

function formatTime(ts: string | number) {
  try {
    let d;
    if (typeof ts === "string") {
      // SQLite returns "YYYY-MM-DD HH:MM:SS" which is UTC but has no timezone indicator.
      // Replace space with T and append Z to make it strict ISO 8601 UTC string.
      const isoString = ts.includes('T') ? ts : ts.replace(' ', 'T') + 'Z';
      d = new Date(isoString);
    } else {
      d = new Date(ts * 1000);
    }
    return d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}

export default function AuditLog({ events }: Props) {
  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-10 h-10 rounded-xl bg-[#12121e] border border-[rgba(255,255,255,0.05)]  flex items-center justify-center text-xl mb-3">
          📋
        </div>
        <p className="text-xs text-[#5a5a80]">Audit events stream here in real-time</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      <AnimatePresence initial={false}>
        {events.map((evt, i) => {
          const actorCfg = ACTOR_CONFIG[evt.actor] || ACTOR_CONFIG.default;
          const outcomeCfg = OUTCOME_CONFIG[evt.rule_outcome] || OUTCOME_CONFIG["n/a"];

          return (
            <motion.div
              key={evt.id}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.25, delay: Math.min(i * 0.02, 0.3) }}
              className="rounded-lg bg-[#0d0d14] border border-[rgba(255,255,255,0.05)]  p-2.5 hover:border-[rgba(108,92,231,0.3)] hover: transition-all group"
            >
              <div className="flex items-start gap-2">
                {/* Outcome dot */}
                <div className="flex-shrink-0 mt-1.5">
                  <div className={clsx("w-1.5 h-1.5 rounded-full", outcomeCfg.dot)} />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5 flex-wrap">
                    <span
                      className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm tracking-wider"
                      style={{ color: actorCfg.color, background: actorCfg.bg }}
                    >
                      {actorCfg.label}
                    </span>
                    <span className="text-[11px] font-mono text-[#a0a0c0] truncate">
                      {evt.action}
                    </span>
                    {evt.amount && (
                      <span className="text-[10px] font-mono text-[#fdcb6e] ml-auto flex-shrink-0">
                        ₹{(evt.amount / 100).toFixed(2)}
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-[#5a5a80] leading-snug truncate group-hover:whitespace-normal group-hover:text-[#a0a0c0] transition-all">
                    {evt.reason}
                  </p>
                  <div className="text-[10px] text-[#5a5a80] mt-0.5 font-mono">
                    {formatTime(evt.timestamp)}
                    {evt.mandate_ref && (
                      <span className="ml-2 text-[#6c5ce7] truncate">
                        ref:{evt.mandate_ref.slice(0, 8)}…
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
