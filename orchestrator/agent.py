"""Orchestrator agent — Claude tool-use loop with mandates, upsell, and policy enforcement."""

import json
import uuid
import os
import time
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from protocol.ap2 import ap2_engine, AP2Phase

from orchestrator.tools import TOOLS, SYSTEM_PROMPT
from catalog.db import search_products, get_product, check_stock
from payments.client import create_order
from payments.models import CartItem
from policy.gate import run_all_checks
from policy.mandates import MandateStore
from upsell.engine import get_upsell_suggestions, UpsellTracker
from campaign.engine import evaluate_campaigns
from audit.logger import log_event

load_dotenv()

MODEL = "gemini-3.5-flash-lite"
MODEL_FALLBACKS = [
    "gemini-3.5-flash",        # baseline speed
    "gemini-3.1-flash-lite",   # legacy fallback
]


class OrchestratorAgent:
    """
    Core orchestrator agent. Manages conversation state, cart, mandates,
    upsell suggestions, and tool dispatch. Uses Claude with tool-use.
    """

    def __init__(self, buyer_id: str = "human"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Add it to your .env file."
            )

        self.client = genai.Client(api_key=api_key)
        self.messages = []
        self.cart: dict[str, CartItem] = {}  # product_id -> CartItem
        self.session_spent: int = 0  # paise already spent this session
        self.pending_blocked_checkout: Optional[dict] = None
        self.session_id = uuid.uuid4().hex[:8]
        self.buyer_id = buyer_id

        # Mandate chain tracking
        self.mandate_store = MandateStore(self.session_id)

        # Upsell tracking
        self.upsell_tracker = UpsellTracker()
        self.last_upsell_suggestions: list[dict] = []

        # Orders created this session
        self.orders: list[dict] = []

        log_event(
            actor="orchestrator",
            action="session_start",
            reason=f"New shopping session started (id: {self.session_id}, buyer: {buyer_id})",
        )

    # ── Cart helpers ──────────────────────────────────────────────────

    def _cart_total(self) -> int:
        return sum(item.subtotal for item in self.cart.values())

    def _cart_summary(self) -> dict:
        items = [item.to_dict() for item in self.cart.values()]
        total = self._cart_total()
        return {
            "items": items,
            "item_count": len(items),
            "total": total,
            "total_display": f"₹{total / 100:.2f}",
        }

    def get_session_state(self) -> dict:
        """Full session state for the dashboard."""
        return {
            "session_id": self.session_id,
            "buyer_id": self.buyer_id,
            "cart": self._cart_summary(),
            "session_spent": self.session_spent,
            "session_spent_display": f"₹{self.session_spent / 100:.2f}",
            "session_cap": 200_000,
            "session_cap_display": "₹2,000.00",
            "session_remaining": 200_000 - self.session_spent,
            "session_remaining_display": f"₹{(200_000 - self.session_spent) / 100:.2f}",
            "spend_pct": min(100, round(self.session_spent / 200_000 * 100, 1)),
            "upsell": self.upsell_tracker.to_dict(),
            "mandates": self.mandate_store.get_all_chains(),
            "current_mandate": self.mandate_store.get_current_chain(),
            "orders": self.orders,
        }

    # ── Tool dispatch ─────────────────────────────────────────────────

    def _dispatch_tool(self, tool_name: str, tool_input: dict) -> str:

        if tool_name == "search_products":
            # AP2: DISCOVER phase
            trace = ap2_engine.get_current_trace()
            if not trace or trace.get("status") in ("completed", "failed"):
                if trace:
                    ap2_engine.clear_trace()
                ap2_engine.start_trace(buyer_agent=self.buyer_id)
            ap2_engine.advance_phase(
                AP2Phase.DISCOVER,
                participant=self.buyer_id,
                detail=f"Catalog search: '{tool_input['query']}'",
            )
            results = search_products(tool_input["query"])
            return json.dumps({"results": results, "count": len(results)})

        elif tool_name == "get_product":
            product = get_product(tool_input["product_id"])
            if product is None:
                return json.dumps({"error": f"Product '{tool_input['product_id']}' not found"})
            return json.dumps(product)

        elif tool_name == "check_stock":
            stock_info = check_stock(tool_input["product_id"])
            if stock_info is None:
                return json.dumps({"error": f"Product '{tool_input['product_id']}' not found"})
            return json.dumps(stock_info)

        elif tool_name == "add_to_cart":
            # AP2: NEGOTIATE phase
            trace = ap2_engine.get_current_trace()
            if not trace or trace.get("status") in ("completed", "failed"):
                if trace:
                    ap2_engine.clear_trace()
                ap2_engine.start_trace(buyer_agent=self.buyer_id)
            ap2_engine.advance_phase(
                AP2Phase.NEGOTIATE,
                participant="merchant",
                detail=f"Item negotiation: {tool_input.get('product_id', '')}",
            )
            return self._handle_add_to_cart(tool_input)

        elif tool_name == "view_cart":
            return json.dumps(self._cart_summary())

        elif tool_name == "remove_from_cart":
            return self._handle_remove_from_cart(tool_input)

        elif tool_name == "checkout":
            return self._handle_checkout()

        elif tool_name == "approve_blocked_checkout":
            return self._handle_approve_blocked(tool_input)

        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _handle_add_to_cart(self, tool_input: dict) -> str:
        product_id = tool_input["product_id"]
        quantity = tool_input.get("quantity", 1)

        product = get_product(product_id)
        if product is None:
            return json.dumps({"error": f"Product '{product_id}' not found"})

        if product["stock"] < quantity:
            log_event(
                actor="orchestrator",
                action="add_to_cart_failed",
                reason=f"Cannot add '{product['name']}' — requested {quantity} but only {product['stock']} in stock",
            )
            if product["stock"] == 0:
                return json.dumps({
                    "error": f"'{product['name']}' is OUT OF STOCK (0 units available)",
                    "suggestion": "Try searching for alternative products in the same category",
                })
            return json.dumps({
                "error": f"Not enough stock for '{product['name']}'. Requested: {quantity}, Available: {product['stock']}",
            })

        if product_id in self.cart:
            self.cart[product_id].quantity += quantity
        else:
            self.cart[product_id] = CartItem(
                product_id=product_id,
                name=product["name"],
                price=product["price"],
                quantity=quantity,
            )

        log_event(
            actor="orchestrator",
            action="add_to_cart",
            reason=f"Added {quantity}x '{product['name']}' (₹{product['price'] / 100:.2f} each) to cart",
            amount=product["price"] * quantity,
        )

        # Generate upsell suggestions after adding to cart
        upsell_info = self._generate_upsell()

        result = {
            "success": True,
            "message": f"Added {quantity}x {product['name']} to cart",
            "cart": self._cart_summary(),
        }
        if upsell_info:
            result["upsell_suggestions"] = upsell_info

        return json.dumps(result)

    def _generate_upsell(self) -> list[dict] | None:
        """Generate upsell suggestions based on current cart."""
        if not self.cart:
            return None

        cart_items_for_upsell = []
        for item in self.cart.values():
            product = get_product(item.product_id)
            if product:
                cart_items_for_upsell.append({
                    "product_id": item.product_id,
                    "name": item.name,
                    "description": product.get("description", ""),
                    "category": product.get("category", ""),
                })

        suggestions = get_upsell_suggestions(cart_items_for_upsell, top_n=2)
        if suggestions:
            self.last_upsell_suggestions = suggestions
            self.upsell_tracker.record_offer(len(suggestions))
            return [{
                "product_id": s["product"]["id"],
                "name": s["product"]["name"],
                "price": s["product"]["price"],
                "price_display": f"₹{s['product']['price'] / 100:.2f}",
                "reason": s["reason"],
                "score": s["relevance_score"],
            } for s in suggestions]
        return None

    def _handle_remove_from_cart(self, tool_input: dict) -> str:
        product_id = tool_input["product_id"]
        if product_id not in self.cart:
            return json.dumps({"error": f"Product '{product_id}' is not in the cart"})

        removed = self.cart.pop(product_id)
        log_event(
            actor="orchestrator",
            action="remove_from_cart",
            reason=f"Removed '{removed.name}' from cart",
        )
        return json.dumps({
            "success": True,
            "message": f"Removed {removed.name} from cart",
            "cart": self._cart_summary(),
        })

    def _handle_checkout(self) -> str:
        if not self.cart:
            return json.dumps({"error": "Cart is empty. Add items before checkout."})

        cart_total = self._cart_total()

        # Track upsell acceptance (items from suggestions that ended up in cart)
        for suggestion in self.last_upsell_suggestions:
            if suggestion["product"]["id"] in self.cart:
                self.upsell_tracker.record_acceptance()

        # Create mandate chain
        cart_items_detail = []
        for item in self.cart.values():
            product = get_product(item.product_id)
            cart_items_detail.append({
                "product_id": item.product_id,
                "name": item.name,
                "price": item.price,
                "quantity": item.quantity,
                "category": product["category"] if product else "unknown",
            })

        # AP2: Start trace if not started
        if not ap2_engine.get_current_trace():
            ap2_engine.start_trace(buyer_agent=self.buyer_id)

        # 1. Intent mandate (from conversation context)
        last_user_msg = ""
        for msg in reversed(self.messages):
            role = msg.get("role") if isinstance(msg, dict) else msg.role
            if role == "user":
                parts = msg.get("parts") if isinstance(msg, dict) else msg.parts
                if parts:
                    p = parts[0]
                    text = p.get("text") if isinstance(p, dict) else getattr(p, "text", "")
                    if text:
                        last_user_msg = text
                        break

        intent = self.mandate_store.create_intent(
            raw_request=last_user_msg or "checkout requested",
            parsed_intent=f"Purchase {len(cart_items_detail)} item(s) totaling ₹{cart_total / 100:.2f}",
            buyer_id=self.buyer_id,
        )

        # AP2: INTENT_LOCK phase
        ap2_engine.advance_phase(
            AP2Phase.INTENT_LOCK,
            participant=self.buyer_id,
            detail=f"Intent locked: {len(cart_items_detail)} items, ₹{cart_total / 100:.2f}",
        )

        # Evaluate Campaigns
        campaign_result = evaluate_campaigns(self.buyer_id, cart_total, len(cart_items_detail), mandate_ref=intent.id)
        final_total = campaign_result["final_total"]
        
        # 2. Cart mandate
        cart_mandate = self.mandate_store.create_cart(
            items=cart_items_detail,
            total_amount=final_total,
            upsell_offered=[s["product"]["name"] for s in self.last_upsell_suggestions] if self.last_upsell_suggestions else [],
            upsell_accepted=[self.cart[s["product"]["id"]].name for s in self.last_upsell_suggestions if s["product"]["id"] in self.cart],
        )

        # 3. Run policy checks
        results = run_all_checks(
            cart_items=cart_items_detail,
            cart_total=final_total,
            session_spent=self.session_spent,
            mandate_ref=intent.id,
        )

        blocked = [r for r in results if not r.allowed]
        policy_dicts = [r.to_dict() for r in results]

        # AP2: POLICY_GATE phase
        if blocked:
            ap2_engine.advance_phase(
                AP2Phase.POLICY_GATE,
                participant="policy_engine",
                detail=f"{len(blocked)} policy check(s) failed",
                success=False,
                failure_reason=blocked[0].reason,
                recovery_action="Requesting buyer override approval",
            )
        else:
            ap2_engine.advance_phase(
                AP2Phase.POLICY_GATE,
                participant="policy_engine",
                detail=f"All {len(results)} policy checks passed",
            )

        if blocked:
            # 4a. Payment mandate — BLOCKED
            payment = self.mandate_store.create_payment(
                policy_checks=policy_dicts,
                approved=False,
                block_reasons=[r.to_dict() for r in blocked],
            )

            self.pending_blocked_checkout = {
                "cart_total": final_total,
                "cart_items": cart_items_detail,
                "block_reasons": [r.to_dict() for r in blocked],
                "campaign": campaign_result,
            }

            return json.dumps({
                "blocked": True,
                "message": "⚠️ Purchase BLOCKED by policy. Buyer approval required.",
                "campaign_message": campaign_result.get("message"),
                "block_reasons": [r.to_dict() for r in blocked],
                "mandate_chain": self.mandate_store.get_current_chain(),
                "instruction": "Show the buyer the block reasons and ask for EXPLICIT approval. Use approve_blocked_checkout if they confirm.",
            })

        # 4b. Payment mandate — APPROVED
        payment = self.mandate_store.create_payment(
            policy_checks=policy_dicts,
            approved=True,
            approval_type="automatic",
        )

        # AP2: PAYMENT phase
        ap2_engine.advance_phase(
            AP2Phase.PAYMENT,
            participant="razorpay",
            detail=f"Creating Razorpay order for ₹{final_total / 100:.2f}",
        )

        resp_json = json.loads(self._create_razorpay_order(final_total, cart_items_detail))

        # AP2: SETTLEMENT phase
        order_id = resp_json.get("order", {}).get("razorpay_order_id", "")
        if resp_json.get("success"):
            ap2_engine.advance_phase(
                AP2Phase.SETTLEMENT,
                participant="razorpay",
                detail=f"Order settled: {order_id}",
            )
            ap2_engine.complete_trace(razorpay_order_id=order_id)
        else:
            ap2_engine.advance_phase(
                AP2Phase.SETTLEMENT,
                participant="razorpay",
                detail="Payment failed",
                success=False,
                failure_reason=resp_json.get("error", "Unknown error"),
                recovery_action="Transaction rolled back, audit trail preserved",
            )

        if campaign_result.get("campaign_id"):
            resp_json["campaign_message"] = campaign_result["message"]
            
        return json.dumps(resp_json)

    def _handle_approve_blocked(self, tool_input: dict) -> str:
        if self.pending_blocked_checkout is None:
            return json.dumps({"error": "No pending blocked checkout to approve."})

        confirmation = tool_input.get("confirmation", "")
        state = self.pending_blocked_checkout
        self.pending_blocked_checkout = None

        # Update mandate
        self.mandate_store.approve_blocked(confirmation)

        return self._create_razorpay_order(state["cart_total"], state["cart_items"])

    def _create_razorpay_order(self, cart_total: int, cart_items: list[dict]) -> str:
        mandate_ref = None
        if self.mandate_store.current_chain and self.mandate_store.current_chain.payment:
            mandate_ref = self.mandate_store.current_chain.payment.id

        try:
            order = create_order(
                amount_paise=cart_total,
                receipt=f"rcpt_{self.session_id}_{uuid.uuid4().hex[:6]}",
                notes={
                    "session_id": self.session_id,
                    "buyer_id": self.buyer_id,
                    "mandate_ref": mandate_ref or "",
                    "items": json.dumps([{"id": i["product_id"], "qty": i["quantity"]} for i in cart_items]),
                },
                mandate_ref=mandate_ref,
            )

            # Update state
            self.session_spent += cart_total
            self.cart.clear()
            self.last_upsell_suggestions = []

            if self.mandate_store.current_chain:
                self.mandate_store.complete_payment(order.get("id", "unknown"))

            order_record = {
                "razorpay_order_id": order.get("id"),
                "amount": order.get("amount"),
                "amount_display": f"₹{order.get('amount', 0) / 100:.2f}",
                "currency": order.get("currency"),
                "status": order.get("status"),
                "receipt": order.get("receipt"),
                "mandate_chain": self.mandate_store.get_current_chain(),
            }
            self.orders.append(order_record)

            log_event(
                actor="ai_buyer" if self.buyer_id.startswith("ai_") else "buyer",
                action="checkout_complete",
                reason=f"Order created: {order.get('id', 'unknown')}",
                mandate_ref=mandate_ref,
                amount=cart_total,
                rule_outcome="allowed",
            )

            # Clear cart and mandate chain for the next purchase
            self.cart = {}
            self.mandate_store.current_chain = None

            return json.dumps({
                "success": True,
                "message": "✅ Order created successfully!",
                "order": order_record,
                "session_spent_display": f"₹{self.session_spent / 100:.2f}",
                "session_remaining": f"₹{(200_000 - self.session_spent) / 100:.2f}",
            })

        except RuntimeError as e:
            log_event(
                actor="razorpay",
                action="checkout_failed",
                reason=f"Payment integration error: {str(e)}",
                mandate_ref=mandate_ref,
                amount=cart_total,
                rule_outcome="blocked",
            )
            return json.dumps({
                "error": str(e),
                "suggestion": "Please configure Razorpay API keys in the .env file",
            })
        except Exception as e:
            log_event(
                actor="razorpay",
                action="checkout_failed",
                reason=f"Unexpected error: {type(e).__name__}: {str(e)}",
                mandate_ref=mandate_ref,
                amount=cart_total,
                rule_outcome="blocked",
            )
            return json.dumps({
                "error": f"Order creation failed: {str(e)}",
                "suggestion": "Please try again or contact support",
            })

    # ── Main conversation loop ────────────────────────────────────────

    def chat(self, user_message: str) -> str:
        log_event(
            actor="buyer" if self.buyer_id == "human" else "ai_buyer",
            action="message",
            reason=f"[{self.buyer_id}] said: {user_message[:200]}",
        )

        self.messages.append({"role": "user", "parts": [types.Part.from_text(text=user_message)]})

        while True:
            # Handle rate limits (429) and unavailable (503) via retry + model fallback
            models_to_try = [MODEL] + MODEL_FALLBACKS
            response = None
            for model_name in models_to_try:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = self.client.models.generate_content(
                            model=model_name,
                            contents=self.messages,
                            config=types.GenerateContentConfig(
                                system_instruction=SYSTEM_PROMPT,
                                tools=TOOLS,
                            )
                        )
                        break  # Success
                    except Exception as e:
                        err_str = str(e).lower()
                        is_retryable = any(k in err_str for k in ["429", "503", "quota", "exhausted", "unavailable", "overloaded", "high demand"])
                        if is_retryable:
                            if attempt < max_retries - 1:
                                sleep_time = 10 * (attempt + 1)
                                log_event(
                                    actor="orchestrator",
                                    action="rate_limit",
                                    reason=f"Model '{model_name}' error: {type(e).__name__}. Waiting {sleep_time}s (retry {attempt + 1})..."
                                )
                                time.sleep(sleep_time)
                                continue
                            else:
                                # Exhausted retries for this model, try next
                                log_event(
                                    actor="orchestrator",
                                    action="model_fallback",
                                    reason=f"Model '{model_name}' exhausted retries. Trying next fallback..."
                                )
                                break
                        raise e
                if response is not None:
                    break
            
            if response is None:
                raise RuntimeError("All models exhausted. Please try again in a minute.")

            if response.function_calls:
                self.messages.append(response.candidates[0].content)

                tool_results = []
                for call in response.function_calls:
                    # Gemini args is usually a dict, but check if we need to convert
                    args_dict = dict(call.args) if call.args else {}
                    
                    log_event(
                        actor="orchestrator",
                        action=f"tool_call:{call.name}",
                        reason=f"Calling '{call.name}' with: {json.dumps(args_dict)[:200]}",
                    )
                    
                    result_str = self._dispatch_tool(call.name, args_dict)
                    
                    # Parse the string result back to dict so it looks nice in Gemini's function response
                    try:
                        result_data = json.loads(result_str)
                    except:
                        result_data = {"result": result_str}
                        
                    tool_results.append(
                        types.Part.from_function_response(
                            name=call.name,
                            response=result_data
                        )
                    )

                self.messages.append({"role": "user", "parts": tool_results})
            else:
                self.messages.append(response.candidates[0].content)
                final_response = response.text or ""
                log_event(
                    actor="orchestrator",
                    action="response",
                    reason=f"Agent responded: {final_response[:200]}",
                )
                return final_response
