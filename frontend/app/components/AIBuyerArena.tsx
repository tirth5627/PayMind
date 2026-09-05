"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { startAIBuyer, getAIBuyerStatus, Persona } from "@/lib/api";
import clsx from "clsx";
import { Play, Loader2, CheckCircle, XCircle, Bot } from "lucide-react";

interface Props {
  personas: Record<string, Persona>;
  onConversationUpdate?: (conversation: ConvEntry[]) => void;
}

interface ConvEntry {
  role: string;
  message: string;
  timestamp: number;
}

const PERSONA_COLORS: Record<string, { gradient: string; glow: string }> = {
  grocery_shopper: { gradient: "from-emerald-600 to-teal-500", glow: "rgba(0,184,148,0.3)" },
  snack_lover: { gradient: "from-amber-600 to-orange-500", glow: "rgba(253,203,110,0.3)" },
  budget_buster: { gradient: "from-rose-600 to-pink-500", glow: "rgba(253,121,168,0.3)" },
  enterprise_buyer: { gradient: "from-blue-600 to-indigo-500", glow: "rgba(116,185,255,0.3)" },
  fraud_tester: { gradient: "from-purple-600 to-violet-500", glow: "rgba(108,92,231,0.3)" },
};

export default function AIBuyerArena({ personas, onConversationUpdate }: Props) {
  const [selectedPersona, setSelectedPersona] = useState<string>("grocery_shopper");
  const [status, setStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [conversation, setConversation] = useState<ConvEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activePersona, setActivePersona] = useState<Persona | null>(null);

  useEffect(() => {
    let isMounted = true;

    const checkStatus = async () => {
      try {
        const statusData = await getAIBuyerStatus();
        if (!isMounted) return;

        if (statusData.status !== "idle") {
          setStatus(statusData.status);
          setConversation(statusData.conversation || []);
          if (statusData.persona) {
            setActivePersona(statusData.persona);
          }

          if (statusData.status === "running") {
            poll();
          }
        }
      } catch {
        // ignore
      }
    };

    const poll = async () => {
      let done = false;
      while (!done && isMounted) {
        await new Promise((r) => setTimeout(r, 1500));
        if (!isMounted) return;
        try {
          const statusData = await getAIBuyerStatus();
          if (!isMounted) return;

          setConversation(statusData.conversation || []);
          onConversationUpdate?.(statusData.conversation || []);

          if (statusData.status === "completed" || statusData.status === "failed") {
            setStatus(statusData.status);
            done = true;
          }
        } catch {
          // ignore
        }
      }
    };

    checkStatus();

    return () => {
      isMounted = false;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


  const launch = async () => {
    setError(null);
    setConversation([]);
    setStatus("running");

    try {
      const result = await startAIBuyer(selectedPersona);
      setActivePersona(result.persona);

      // Poll for status updates
      const poll = async () => {
        let done = false;
        while (!done) {
          await new Promise((r) => setTimeout(r, 1500));
          try {
            const statusData = await getAIBuyerStatus();
            setConversation(statusData.conversation || []);
            onConversationUpdate?.(statusData.conversation || []);

            if (statusData.status === "completed" || statusData.status === "failed") {
              setStatus(statusData.status);
              done = true;
            }
          } catch {
            // ignore poll errors
          }
        }
      };

      poll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setError(msg);
      setStatus("idle");
    }
  };

  const personaColors = PERSONA_COLORS[selectedPersona] || PERSONA_COLORS.grocery_shopper;
  const selectedPersonaData = personas[selectedPersona];

  return (
    <div className="space-y-3">
      {/* Persona selector */}
      <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
        {Object.entries(personas).map(([key, persona]) => {
          const colors = PERSONA_COLORS[key] || PERSONA_COLORS.grocery_shopper;
          const isSelected = selectedPersona === key;
          return (
            <motion.button
              key={key}
              id={`persona-${key}`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setSelectedPersona(key)}
              disabled={status === "running"}
              className={clsx(
                "p-2.5 rounded-xl border text-left transition-all relative overflow-hidden disabled:opacity-50",
                isSelected
                  ? "border-[rgba(108,92,231,0.3)] bg-purple-50/50 "
                  : "border-[rgba(255,255,255,0.05)] bg-[#0d0d14] hover:border-[rgba(108,92,231,0.2)]"
              )}
              style={isSelected ? { boxShadow: `0 0 16px ${colors.glow}` } : {}}
            >
              {isSelected && (
                <motion.div
                  layoutId="persona-bg"
                  className={clsx("absolute inset-0 opacity-10 bg-gradient-to-br", colors.gradient)}
                />
              )}
              <div className="relative z-10">
                <div className="text-xl mb-1">{persona.emoji}</div>
                <div className="text-xs font-semibold text-white truncate">{persona.name}</div>
                <div className="text-[10px] text-[#5a5a80]">₹{persona.budget.toLocaleString()}</div>
              </div>
            </motion.button>
          );
        })}
      </div>

      {/* Selected persona detail */}
      {selectedPersonaData && (
        <motion.div
          key={selectedPersona}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-3 rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] text-xs "
        >
          <p className="text-[#a0a0c0] leading-relaxed">{selectedPersonaData.description}</p>
        </motion.div>
      )}

      {/* Launch button */}
      <motion.button
        id="btn-launch-ai-buyer"
        whileHover={status !== "running" ? { scale: 1.02 } : {}}
        whileTap={status !== "running" ? { scale: 0.98 } : {}}
        onClick={launch}
        disabled={status === "running"}
        className={clsx(
          "w-full py-2.5 rounded-xl font-semibold text-sm flex items-center justify-center gap-2 transition-all",
          status === "running"
            ? "bg-purple-50 border border-[rgba(108,92,231,0.2)] text-[#6c5ce7]"
            : `bg-gradient-to-r ${personaColors.gradient} text-white shadow-lg`
        )}
        style={status !== "running" ? { boxShadow: `0 4px 24px ${personaColors.glow}` } : {}}
      >
        {status === "running" ? (
          <>
            <Loader2 size={14} className="animate-spin" />
            AI Buyer Shopping…
          </>
        ) : (
          <>
            <Play size={14} />
            Launch {selectedPersonaData?.name || "AI Buyer"}
          </>
        )}
      </motion.button>

      {error && (
        <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex gap-2">
          <XCircle size={12} className="flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      {/* Conversation stream */}
      <AnimatePresence>
        {conversation.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className="space-y-2 max-h-64 overflow-y-auto"
          >
            {status === "completed" && (
              <div className="flex items-center gap-2 text-emerald-400 text-xs font-semibold py-1">
                <CheckCircle size={12} />
                Shopping complete!
              </div>
            )}
            {conversation.map((entry, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: entry.role === "buyer" ? -8 : 8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.2 }}
                className={clsx("flex gap-2", entry.role === "buyer" ? "justify-start" : "justify-end")}
              >
                {entry.role === "buyer" && (
                  <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-600 to-pink-500 flex items-center justify-center text-[10px] flex-shrink-0 mt-1">
                    {activePersona?.emoji || "🤖"}
                  </div>
                )}
                <div
                  className={clsx(
                    "max-w-[85%] rounded-xl p-2.5 text-[11px] leading-relaxed",
                    entry.role === "buyer"
                      ? "bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] text-[#a0a0c0] rounded-tl-sm "
                      : "bg-teal-50 border border-[rgba(0,206,201,0.2)] text-[#00cec9] rounded-tr-sm "
                  )}
                >
                  <div className="text-[9px] font-bold uppercase tracking-wider mb-1 opacity-60">
                    {entry.role === "buyer" ? (activePersona?.name || "AI Buyer") : "Merchant Agent"}
                  </div>
                  {entry.message}
                </div>
                {entry.role === "merchant" && (
                  <div className="w-6 h-6 rounded-md bg-gradient-to-br from-teal-600 to-blue-500 flex items-center justify-center text-[10px] flex-shrink-0 mt-1">
                    🏪
                  </div>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
