"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getAgentCatalog } from "@/lib/api";
import { Copy, Check, Globe, Zap } from "lucide-react";

export default function AgentCatalog() {
  const [catalog, setCatalog] = useState<unknown>(null);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAgentCatalog()
      .then((data) => {
        setCatalog(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleCopy = () => {
    if (catalog) {
      navigator.clipboard.writeText(JSON.stringify(catalog, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-8">
        <div className="w-6 h-6 border-2 border-purple-500/30 border-t-purple-500 rounded-full animate-spin mb-3" />
        <p className="text-xs text-[#5a5a80]">Loading agent catalog...</p>
      </div>
    );
  }

  const items = (catalog as { itemListElement?: { item: { name: string; productID: string; offers: { price: string; availability: string } } }[] })?.itemListElement || [];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe size={14} className="text-[#00cec9]" />
          <span className="text-xs font-semibold text-white">Schema.org JSON-LD</span>
        </div>
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#12121e] border border-[rgba(0,206,201,0.2)] text-[10px] text-[#00cec9] hover:border-[rgba(0,206,201,0.4)] transition-all"
        >
          {copied ? <Check size={10} /> : <Copy size={10} />}
          {copied ? "Copied!" : "Copy for AI Agent"}
        </motion.button>
      </div>

      {/* Info banner */}
      <div className="rounded-xl bg-[rgba(0,206,201,0.05)] border border-[rgba(0,206,201,0.15)] p-3">
        <div className="flex items-start gap-2">
          <Zap size={12} className="text-[#00cec9] mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-[10px] text-[#00cec9] font-semibold mb-0.5">AI-Agent Discoverable</p>
            <p className="text-[10px] text-[#a0a0c0] leading-relaxed">
              This catalog is served at <code className="text-[#6c5ce7] text-[9px]">/api/catalog/agent-readable</code> in
              Schema.org JSON-LD format. Any AI agent following web standards can discover and purchase from this merchant.
            </p>
          </div>
        </div>
      </div>

      {/* Product cards from JSON-LD */}
      <div className="space-y-2">
        {items.map((item, i) => {
          const product = item.item;
          const isInStock = product.offers?.availability?.includes("InStock");
          return (
            <motion.div
              key={product.productID || i}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="rounded-lg bg-[#0d0d14] border border-[rgba(255,255,255,0.04)] p-3 hover:border-[rgba(0,206,201,0.2)] transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-white">{product.name}</span>
                <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${
                  isInStock ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"
                }`}>
                  {isInStock ? "IN STOCK" : "OUT OF STOCK"}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] text-[#00cec9] font-mono font-bold">₹{product.offers?.price}</span>
                <span className="text-[9px] text-[#5a5a80] font-mono">{product.productID}</span>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Raw JSON preview */}
      <details className="group">
        <summary className="text-[10px] text-[#5a5a80] cursor-pointer hover:text-[#a0a0c0] transition-colors">
          View raw JSON-LD ▸
        </summary>
        <pre className="mt-2 rounded-lg bg-[#0d0d14] border border-[rgba(255,255,255,0.04)] p-3 text-[9px] text-[#a0a0c0] font-mono overflow-x-auto max-h-60 overflow-y-auto leading-relaxed">
          {JSON.stringify(catalog, null, 2)}
        </pre>
      </details>
    </div>
  );
}
