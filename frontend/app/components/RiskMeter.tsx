"use client";

import { motion } from "framer-motion";
import { RiskScore } from "@/lib/api";
import { ShieldAlert, ShieldCheck, ShieldOff, Shield } from "lucide-react";
import { RadialBarChart, RadialBar, ResponsiveContainer, Cell } from "recharts";

interface Props {
  riskScore: RiskScore | null;
}

const LEVEL_CONFIG = {
  low: {
    icon: ShieldCheck,
    color: "#00b894",
    bg: "rgba(0,184,148,0.1)",
    border: "rgba(0,184,148,0.3)",
    label: "LOW RISK",
  },
  medium: {
    icon: Shield,
    color: "#f39c12",
    bg: "rgba(243,156,18,0.1)",
    border: "rgba(243,156,18,0.3)",
    label: "MEDIUM RISK",
  },
  high: {
    icon: ShieldAlert,
    color: "#e17055",
    bg: "rgba(225,112,85,0.1)",
    border: "rgba(225,112,85,0.3)",
    label: "HIGH RISK",
  },
  critical: {
    icon: ShieldOff,
    color: "#d63031",
    bg: "rgba(214,48,49,0.1)",
    border: "rgba(214,48,49,0.3)",
    label: "CRITICAL",
  },
};

export default function RiskMeter({ riskScore }: Props) {
  if (!riskScore) {
    return (
      <div className="h-24 flex items-center justify-center">
        <p className="text-xs text-[#5a5a80]">Risk meter initializes after first action</p>
      </div>
    );
  }

  const config = LEVEL_CONFIG[riskScore.level];
  const IconComp = config.icon;
  const chartData = [
    { value: riskScore.score, fill: riskScore.color },
    { value: 100 - riskScore.score, fill: "rgba(255,255,255,0.05)" },
  ];

  return (
    <div className="space-y-3">
      {/* Score dial */}
      <div className="flex items-center gap-4">
        <div className="relative w-20 h-20 flex-shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <RadialBarChart
              cx="50%"
              cy="50%"
              innerRadius="60%"
              outerRadius="100%"
              startAngle={90}
              endAngle={-270}
              data={chartData}
              barSize={8}
            >
              <RadialBar dataKey="value" cornerRadius={4}>
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </RadialBar>
            </RadialBarChart>
          </ResponsiveContainer>
          {/* Center score */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-lg font-bold font-mono" style={{ color: riskScore.color }}>
              {riskScore.score.toFixed(0)}
            </span>
          </div>
        </div>

        <div className="flex-1">
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            key={riskScore.level}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold mb-1.5"
            style={{
              color: config.color,
              background: config.bg,
              border: `1px solid ${config.border}`,
            }}
          >
            <IconComp size={11} />
            {config.label}
          </motion.div>
          <p className="text-[11px] text-[#a0a0c0] leading-relaxed">{riskScore.recommendation}</p>
        </div>
      </div>

      {/* Risk factors */}
      {riskScore.factors.length > 0 && (
        <div className="space-y-2">
          {riskScore.factors.map((factor, i) => (
            <motion.div
              key={factor.name}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[11px] text-[#a0a0c0]">{factor.name}</span>
                <span className="text-[11px] font-mono font-semibold" style={{ color: riskScore.color }}>
                  {factor.score.toFixed(0)}/100
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-[#12121e] overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${factor.score}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                  className="h-full rounded-full"
                  style={{ background: riskScore.color }}
                />
              </div>
              <p className="text-[10px] text-[#5a5a80] mt-0.5">{factor.detail}</p>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
