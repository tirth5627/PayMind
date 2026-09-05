"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Mic, RotateCcw, Zap } from "lucide-react";
import { sendChat, SessionState, AuditEvent } from "@/lib/api";
import clsx from "clsx";

interface Message {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: number;
}

interface Props {
  onSessionUpdate?: (session: SessionState) => void;
}

const SUGGESTIONS = [
  { icon: "🥬", label: "Browse groceries", query: "I need groceries for the week" },
  { icon: "🍫", label: "Find snacks", query: "Show me the best snacks and chocolate" },
  { icon: "🔌", label: "Electronics", query: "What electronics do you have?" },
  { icon: "💰", label: "Best deals", query: "Show me your best deals today" },
];

export default function ChatPanel({ onSessionUpdate }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text?: string) => {
    const msg = (text || input).trim();
    if (!msg || loading) return;

    setInput("");
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: msg,
      timestamp: Date.now(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const data = await sendChat(msg);
      const agentMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: data.response,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, agentMsg]);
      onSessionUpdate?.(data.session);
    } catch (err) {
      const errMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: `⚠️ Connection error. Make sure the backend is running on port 8000.`,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-8">
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, type: "spring" }}
              className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600 to-teal-500 flex items-center justify-center text-3xl mb-4 glow-purple"
            >
              🤖
            </motion.div>
            <h3 className="text-lg font-semibold text-white mb-2">Welcome to AgenticMart</h3>
            <p className="text-sm text-[#a0a0c0] mb-6 max-w-xs">
              I'm your AI commerce orchestrator. Every purchase I make is governed, audited, and mandate-chained.
            </p>
            <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
              {SUGGESTIONS.map((s) => (
                <motion.button
                  key={s.query}
                  whileHover={{ scale: 1.03, y: -2 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={() => handleSend(s.query)}
                  id={`suggestion-${s.label.toLowerCase().replace(/\s+/g, "-")}`}
                  className="flex items-center gap-2 p-3 rounded-xl bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] hover:border-[rgba(108,92,231,0.3)] hover: transition-all text-left text-sm text-[#a0a0c0]"
                >
                  <span>{s.icon}</span>
                  <span className="text-[#a0a0c0]">{s.label}</span>
                </motion.button>
              ))}
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={clsx("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}
              >
                {msg.role === "agent" && (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-teal-500 flex items-center justify-center text-sm flex-shrink-0 mt-1">
                    🤖
                  </div>
                )}
                <div
                  className={clsx(
                    "max-w-[80%] rounded-2xl p-3.5 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "bg-gradient-to-r from-purple-600 to-purple-500 text-white rounded-tr-sm"
                      : "bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] text-[#f0f0ff] rounded-tl-sm "
                  )}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  <div className="text-xs mt-1.5 opacity-50">
                    {new Date(msg.timestamp).toLocaleTimeString()}
                  </div>
                </div>
                {msg.role === "user" && (
                  <div className="w-8 h-8 rounded-lg bg-[#6c5ce7] flex items-center justify-center text-sm flex-shrink-0 mt-1">
                    👤
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}

        {loading && (
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3"
          >
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-600 to-teal-500 flex items-center justify-center text-sm flex-shrink-0">
              🤖
            </div>
            <div className="bg-[#0d0d14]  border border-[rgba(255,255,255,0.05)] rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1.5 items-center h-4">
                {[0, 0.15, 0.3].map((delay, i) => (
                  <motion.div
                    key={i}
                    animate={{ y: [0, -4, 0] }}
                    transition={{ duration: 0.6, repeat: Infinity, delay }}
                    className="w-1.5 h-1.5 rounded-full bg-purple-400"
                  />
                ))}
              </div>
            </div>
          </motion.div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-[rgba(255,255,255,0.05)]">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <input
              id="chat-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKey}
              placeholder="Tell me what you need..."
              disabled={loading}
              className="w-full bg-[#0d0d14] border border-[rgba(255,255,255,0.05)] focus:border-purple-500 rounded-2xl px-5 py-3.5 text-sm text-[#f0f0ff] placeholder:text-[#5a5a80] outline-none transition-all  disabled:opacity-50"
            />
          </div>
          <motion.button
            id="btn-send"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="w-12 h-12 rounded-2xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-white disabled:opacity-40 disabled:cursor-not-allowed shadow-[0_0_20px_rgba(108,92,231,0.3)] transition-all"
          >
            <Send size={18} className={loading ? "opacity-0" : ""} />
            {loading && <div className="absolute w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
          </motion.button>
        </div>
      </div>
    </div>
  );
}
