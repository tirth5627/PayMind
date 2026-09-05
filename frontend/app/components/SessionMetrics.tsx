"use client";

import { motion } from "framer-motion";
import { SessionState } from "@/lib/api";
import { ShoppingCart, Wallet, TrendingUp, Package } from "lucide-react";

interface Props {
  session: SessionState | null;
}

export default function SessionMetrics({ session }: Props) {
  if (!session) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] animate-pulse" />
        ))}
      </div>
    );
  }

  const spendPct = session.spend_pct || 0;
  const spendColor =
    spendPct < 50 ? "#00b894" : spendPct < 80 ? "#f39c12" : "#d63031";

  const metrics = [
    {
      icon: Wallet,
      label: "Session Spend",
      value: session.session_spent_display,
      sub: `of ${session.session_cap_display} cap`,
      color: spendColor,
      bar: spendPct,
      id: "metric-spend",
    },
    {
      icon: ShoppingCart,
      label: "Cart Items",
      value: session.cart.item_count.toString(),
      sub: session.cart.total_display,
      color: "#6c5ce7",
      id: "metric-cart",
    },
    {
      icon: TrendingUp,
      label: "Upsell Rate",
      value: session.upsell.acceptance_rate_display,
      sub: `${session.upsell.accepted}/${session.upsell.offered} accepted`,
      color: "#00cec9",
      id: "metric-upsell",
    },
    {
      icon: Package,
      label: "Orders",
      value: session.orders.length.toString(),
      sub: "this session",
      color: "#fdcb6e",
      id: "metric-orders",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {metrics.map((m, i) => (
        <motion.div
          key={m.id}
          id={m.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)]  p-3.5 relative overflow-hidden"
        >
          {/* Icon */}
          <div
            className="w-7 h-7 rounded-lg flex items-center justify-center mb-2"
            style={{ background: `${m.color}22` }}
          >
            <m.icon size={14} style={{ color: m.color }} />
          </div>

          {/* Value */}
          <div className="text-lg font-bold font-mono text-white leading-none mb-0.5">
            {m.value}
          </div>

          {/* Label */}
          <div className="text-[10px] text-[#5a5a80] uppercase tracking-wider font-semibold">
            {m.label}
          </div>
          <div className="text-[10px] text-[#5a5a80] mt-0.5">{m.sub}</div>

          {/* Spend bar */}
          {m.bar !== undefined && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#12121e]">
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${m.bar}%` }}
                transition={{ duration: 1, ease: "easeOut" }}
                className="h-full"
                style={{ background: m.color }}
              />
            </div>
          )}
        </motion.div>
      ))}
    </div>
  );
}
