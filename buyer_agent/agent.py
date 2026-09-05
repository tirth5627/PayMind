"""AI Buyer Agent — autonomous second agent that shops with no human in the loop.

This is THE differentiator: a separate Claude instance with its own persona and
budget that discovers products, builds a cart, handles failures, and completes
a purchase entirely autonomously. Most hackathon teams build chatbots — this
demonstrates genuine agent-to-agent commerce.
"""

import json
import os
import threading
import time
from typing import Optional, Callable
from dotenv import load_dotenv
from google import genai
from google.genai import types

from orchestrator.agent import OrchestratorAgent
from audit.logger import log_event

load_dotenv()

MODEL = "gemini-3.5-flash-lite"

BUYER_PERSONAS = {
    "grocery_shopper": {
        "name": "GroceryBot",
        "goal": "Buy groceries for the week — rice, dal, and some healthy snacks",
        "budget": 1500,
        "style": "efficient, health-conscious, looks for value",
        "emoji": "🥬",
        "description": "Methodical weekly shopper. Checks prices, avoids impulse buys.",
    },
    "snack_lover": {
        "name": "SnackHunter",
        "goal": "Find the best snacks and chocolate available, treat yourself",
        "budget": 800,
        "style": "indulgent, loves chocolate and nuts, doesn't mind spending on quality",
        "emoji": "🍫",
        "description": "Hedonistic snack enthusiast. Targets premium treats.",
    },
    "budget_buster": {
        "name": "BigSpender",
        "goal": "Buy premium items including electronics — test the spend cap limits",
        "budget": 3000,
        "style": "wants the best of everything, will push against spending limits",
        "emoji": "💸",
        "description": "High-roller. Deliberately hits policy limits to test overrides.",
    },
    "enterprise_buyer": {
        "name": "ProcureBot-9000",
        "goal": "Source bulk office supplies and nutritional snacks for a 50-person team. Needs receipts and justification for every purchase.",
        "budget": 5000,
        "style": "formal, asks for bulk discounts, demands itemized receipts, slow and methodical",
        "emoji": "🏢",
        "description": "Corporate procurement agent. Requires full mandate chain + justification logs.",
    },
    "fraud_tester": {
        "name": "EdgeCaseBot",
        "goal": "Probe the system: try to buy out-of-stock items, exceed spend caps, attempt double-checkout, and see what breaks",
        "budget": 10000,
        "style": "adversarial, creative, tries unusual purchase patterns and edge cases",
        "emoji": "🔍",
        "description": "Red-team agent. Systematically tests every policy boundary and failure mode.",
    },
}


def _build_buyer_system_prompt(persona: dict) -> str:
    return f"""You are {persona['name']}, an autonomous AI shopping assistant acting on behalf of a user.

Your shopping goal: {persona['goal']}
Your budget: ₹{persona['budget']}
Your shopping style: {persona['style']}

You are interacting with AgenticMart's shopping assistant. You must:
1. Browse the catalog by searching for relevant products
2. Check stock availability before adding items
3. Build a cart that matches your goal and stays within budget
4. Request checkout when your cart is ready
5. If a purchase is blocked (spend cap, etc.), evaluate whether to approve or modify your cart
6. Handle any errors gracefully (out of stock, etc.)

IMPORTANT RULES:
- You must complete your shopping in at most 8 messages
- Always check prices and stay within your budget of ₹{persona['budget']}
- If something is out of stock, find an alternative
- If the spend cap blocks you, either reduce your cart OR approve the override if you're confident
- Be decisive — don't browse endlessly
- If you want to abort the shopping trip without buying anything, say exactly "TERMINATE_SHOPPING"

Respond naturally as if you're talking to a store assistant. Start by telling them what you're looking for."""


class AIBuyerAgent:
    """
    Autonomous buyer agent that drives a complete purchase flow.
    Runs in a background thread and reports progress via callbacks.
    """

    def __init__(
        self,
        persona_key: str = "grocery_shopper",
        on_message: Optional[Callable] = None,
        ws_queue=None,
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")

        self.api_key = api_key
        self.client = None
        self.persona = BUYER_PERSONAS.get(persona_key, BUYER_PERSONAS["grocery_shopper"])
        self.persona_key = persona_key
        self.on_message = on_message  # callback(role, message)
        self.ws_queue = ws_queue  # asyncio.Queue for WebSocket streaming

        # The merchant-side orchestrator this buyer talks to will be initialized in run()
        self.merchant_agent = None

        self.conversation: list[dict] = []
        self.status: str = "idle"  # idle → running → completed → failed
        self.max_turns: int = 10
        self.result: Optional[dict] = None

        log_event(
            actor="ai_buyer",
            action="buyer_initialized",
            reason=f"AI Buyer '{self.persona['name']}' initialized — goal: {self.persona['goal']}, budget: ₹{self.persona['budget']}",
        )

    def _emit(self, role: str, message: str):
        """Emit a message to the callback and store in conversation."""
        entry = {"role": role, "message": message, "timestamp": time.time()}
        self.conversation.append(entry)
        if self.on_message:
            try:
                self.on_message(entry)
            except Exception:
                pass
        # Push to WebSocket queue if connected
        if self.ws_queue is not None:
            try:
                import asyncio, json
                event = {
                    "type": "ai_buyer_message",
                    "role": role,
                    "message": message,
                    "persona": self.persona.get("name"),
                    "persona_key": self.persona_key,
                    "timestamp": entry["timestamp"],
                }
                self.ws_queue.put_nowait(json.dumps(event))
            except Exception:
                pass

    def _get_buyer_response(self, merchant_message: str) -> str:
        """Get the AI buyer's next message in response to the merchant."""
        messages = []

        # Build conversation history for the buyer
        for entry in self.conversation:
            if entry["role"] == "buyer":
                messages.append({"role": "model", "parts": [types.Part.from_text(text=entry["message"])]})
            elif entry["role"] == "merchant":
                messages.append({"role": "user", "parts": [types.Part.from_text(text=entry["message"])]})

        # Add latest merchant message
        if merchant_message:
            messages.append({"role": "user", "parts": [types.Part.from_text(text=merchant_message)]})

        # If no messages yet, start the conversation
        if not messages:
            messages.append({"role": "user", "parts": [types.Part.from_text(text="Welcome to AgenticMart! How can I help you today?")]})

        models_to_try = [
            MODEL,
            "gemini-3.5-flash",
            "gemini-3.1-flash-lite",
        ]
        for model_name in models_to_try:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=messages,
                        config=types.GenerateContentConfig(
                            system_instruction=_build_buyer_system_prompt(self.persona),
                            temperature=0.7,
                        )
                    )
                    return response.text or ""
                except Exception as e:
                    err_str = str(e).lower()
                    is_retryable = any(k in err_str for k in ["429", "503", "quota", "exhausted", "unavailable", "overloaded", "high demand"])
                    if is_retryable:
                        if attempt < max_retries - 1:
                            sleep_time = 10 * (attempt + 1)
                            log_event(
                                actor="ai_buyer",
                                action="rate_limit",
                                reason=f"Model '{model_name}' error: {type(e).__name__}. Waiting {sleep_time}s (retry {attempt + 1})..."
                            )
                            time.sleep(sleep_time)
                            continue
                        else:
                            log_event(
                                actor="ai_buyer",
                                action="model_fallback",
                                reason=f"Model '{model_name}' exhausted retries. Trying next fallback..."
                            )
                            break
                    raise e
        return ""

    def run(self) -> dict:
        """
        Execute the full autonomous shopping flow.
        Returns a result dict with status, conversation, and outcome.
        """
        self.status = "running"
        
        # Initialize clients in the background thread to prevent asyncio Event Loop errors
        if not self.client:
            self.client = genai.Client(api_key=self.api_key)
        if not self.merchant_agent:
            self.merchant_agent = OrchestratorAgent(buyer_id=f"ai_{self.persona_key}")

        log_event(
            actor="ai_buyer",
            action="shopping_started",
            reason=f"AI Buyer '{self.persona['name']}' starting autonomous shopping",
        )

        try:
            # The buyer starts the conversation
            buyer_msg = self._get_buyer_response("")
            self._emit("buyer", buyer_msg)

            for turn in range(self.max_turns):
                # Send buyer's message to the merchant orchestrator
                log_event(
                    actor="ai_buyer",
                    action="buyer_message",
                    reason=f"[Turn {turn + 1}] Buyer: {buyer_msg[:150]}",
                )

                merchant_response = self.merchant_agent.chat(buyer_msg)
                self._emit("merchant", merchant_response)

                log_event(
                    actor="ai_buyer",
                    action="merchant_response",
                    reason=f"[Turn {turn + 1}] Merchant: {merchant_response[:150]}",
                )

                # Check if shopping is done (order created or cart cleared)
                if any(keyword in merchant_response.lower() for keyword in
                       ["order created", "order has been created", "razorpay_order_id", "order_"]):
                    self.status = "completed"
                    log_event(
                        actor="ai_buyer",
                        action="shopping_completed",
                        reason=f"AI Buyer '{self.persona['name']}' completed purchase",
                    )
                    break

                # Get buyer's next response
                buyer_msg = self._get_buyer_response(merchant_response)
                self._emit("buyer", buyer_msg)

                # Check if buyer wants to abort
                if any(keyword in buyer_msg for keyword in
                       ["TERMINATE_SHOPPING", "CANCEL_SHOPPING"]):
                    self.status = "completed"
                    break

            else:
                self.status = "completed"
                log_event(
                    actor="ai_buyer",
                    action="shopping_max_turns",
                    reason=f"AI Buyer reached max turns ({self.max_turns})",
                )

            self.result = {
                "status": self.status,
                "persona": self.persona,
                "turns": len(self.conversation),
                "conversation": self.conversation,
                "merchant_session": {
                    "session_spent": self.merchant_agent.session_spent,
                    "cart_remaining": self.merchant_agent._cart_summary(),
                },
            }
            return self.result

        except Exception as e:
            self.status = "failed"
            log_event(
                actor="ai_buyer",
                action="shopping_failed",
                reason=f"AI Buyer error: {type(e).__name__}: {str(e)}",
            )
            self.result = {
                "status": "failed",
                "error": str(e),
                "conversation": self.conversation,
            }
            return self.result

    def run_async(self) -> threading.Thread:
        """Run the shopping flow in a background thread."""
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        return thread
