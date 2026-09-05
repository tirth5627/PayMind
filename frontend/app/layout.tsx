import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PayMind — AI Payment Governance Layer | AgenticMart",
  description:
    "The world's first agentic payment conscience. Enforce spending mandates, audit AI transactions in real-time, and govern autonomous agent commerce with cryptographic accountability.",
  keywords: ["AI payments", "agentic commerce", "Razorpay", "payment governance", "AI agents"],
  openGraph: {
    title: "PayMind — AI Payment Governance",
    description: "Real-time mandate enforcement for the AI agent economy",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrainsMono.variable}`}>
      <body className="antialiased bg-[#050508] text-white overflow-x-hidden">
        {children}
      </body>
    </html>
  );
}
