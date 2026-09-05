"use client";

import { motion, AnimatePresence } from "framer-motion";
import { MandateChain } from "@/lib/api";
import { CheckCircle, Clock, XCircle, ShoppingCart, FileText, CreditCard } from "lucide-react";
import clsx from "clsx";

interface Props {
  chain: MandateChain | null;
}

const stepConfig = [
  {
    key: "intent",
    label: "Intent",
    icon: FileText,
    color: "#6c5ce7",
    glow: "rgba(108,92,231,0.4)",
    description: "Buyer's raw request captured and parsed",
  },
  {
    key: "cart",
    label: "Cart",
    icon: ShoppingCart,
    color: "#00cec9",
    glow: "rgba(0,206,201,0.4)",
    description: "Items, quantities and subtotals verified",
  },
  {
    key: "payment",
    label: "Payment",
    icon: CreditCard,
    color: "#fd79a8",
    glow: "rgba(253,121,168,0.4)",
    description: "Policy checks passed → Razorpay order created",
  },
];

function StepStatus({ filled, blocked }: { filled: boolean; blocked?: boolean }) {
  if (!filled) return <Clock size={14} className="text-[#5a5a80]" />;
  if (blocked) return <XCircle size={14} className="text-red-400" />;
  return <CheckCircle size={14} className="text-emerald-400" />;
}

export default function MandateVisualizer({ chain }: Props) {
  const hasIntent = !!chain?.intent;
  const hasCart = !!chain?.cart;
  const hasPayment = !!chain?.payment;
  const isBlocked = chain?.payment && !chain.payment.approved;

  const steps = [
    { ...stepConfig[0], filled: hasIntent, blocked: false, data: chain?.intent },
    { ...stepConfig[1], filled: hasCart, blocked: false, data: chain?.cart },
    { ...stepConfig[2], filled: hasPayment, blocked: isBlocked, data: chain?.payment },
  ];

  return (
    <div className="space-y-3">
      {/* Chain visualization */}
      <div className="flex items-center gap-1">
        {steps.map((step, i) => (
          <div key={step.key} className="flex items-center flex-1">
            {/* Node */}
            <motion.div
              animate={step.filled ? { boxShadow: `0 0 16px ${step.glow}` } : {}}
              transition={{ duration: 0.5 }}
              className={clsx(
                "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center border transition-all",
                step.filled
                  ? "border-opacity-60"
                  : "border-[rgba(255,255,255,0.05)] bg-[#12121e] text-[#5a5a80]"
              )}
              style={
                step.filled
                  ? { borderColor: step.color, background: `${step.color}22` }
                  : {}
              }
            >
              <step.icon
                size={16}
                style={{ color: step.filled ? step.color : "#5a5a80" }}
              />
            </motion.div>

            {/* Connector */}
            {i < steps.length - 1 && (
              <div className="flex-1 h-px mx-1 relative overflow-hidden">
                <div
                  className={clsx(
                    "absolute inset-0 transition-colors duration-500",
                    step.filled ? "bg-gradient-to-r from-purple-500 to-teal-500" : "bg-[#12121e]"
                  )}
                />
                {step.filled && (
                  <motion.div
                    animate={{ x: ["0%", "300%"] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    className="absolute inset-0 w-1/3 bg-gradient-to-r from-transparent via-white/40 to-transparent"
                  />
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Step labels */}
      <div className="flex gap-1">
        {steps.map((step) => (
          <div key={step.key} className="flex-1">
            <div className="flex items-center gap-1 mb-0.5">
              <StepStatus filled={step.filled} blocked={step.blocked || false} />
              <span className="text-xs font-semibold" style={{ color: step.filled ? step.color : "#5a5a80" }}>
                {step.label}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Detail card */}
      <AnimatePresence mode="wait">
        {chain && (
          <motion.div
            key={chain.id || "chain"}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)]  p-3 space-y-2"
          >
            {hasIntent && chain.intent && (
              <div>
                <div className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider mb-1">
                  Intent
                </div>
                <p className="text-xs text-[#a0a0c0] leading-relaxed">
                  {chain.intent.parsed_intent}
                </p>
              </div>
            )}
            {hasCart && chain.cart && (
              <div>
                <div className="text-[10px] font-semibold text-teal-400 uppercase tracking-wider mb-1">
                  Cart
                </div>
                <p className="text-xs text-[#a0a0c0]">
                  {chain.cart.items?.length ?? 0} item(s) ·{" "}
                  <span className="text-white font-mono">
                    ₹{((chain.cart.total_amount || 0) / 100).toFixed(2)}
                  </span>
                </p>
              </div>
            )}
            {hasPayment && chain.payment && (
              <div>
                <div className="text-[10px] font-semibold text-pink-400 uppercase tracking-wider mb-1">
                  Payment
                </div>
                <div
                  className={clsx(
                    "inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium",
                    chain.payment.approved
                      ? "bg-emerald-500/20 text-emerald-400"
                      : "bg-red-500/20 text-red-400"
                  )}
                >
                  {chain.payment.approved ? "✓ APPROVED" : "✗ BLOCKED"}
                  {chain.payment.approval_type && ` · ${chain.payment.approval_type}`}
                </div>
              </div>
            )}
            {chain.razorpay_order_id && (
              <div className="pt-1 border-t border-[rgba(255,255,255,0.05)]">
                <div className="text-[10px] font-semibold text-[#fdcb6e] uppercase tracking-wider mb-1">
                  Razorpay Order
                </div>
                <p className="text-xs font-mono text-[#fdcb6e] truncate">{chain.razorpay_order_id}</p>
              </div>
            )}
          </motion.div>
        )}
        {!chain && (
          <motion.div
            key="empty"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl bg-[#12121e] border border-[rgba(255,255,255,0.05)] p-4 text-center text-[#5a5a80] "
          >
            <p className="text-xs text-[#5a5a80]">
              Mandate chain will form when you start shopping
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
