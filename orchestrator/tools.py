"""Tool definitions for the orchestrator agent (Gemini Function declarations)."""

TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_products",
                "description": (
                    "Search the product catalog by keyword. Matches against product name, "
                    "description, and category. Use this when the buyer asks about products, "
                    "wants recommendations, or is browsing."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Search term (e.g. 'snacks', 'rice', 'electronics', 'chocolate')",
                        }
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "get_product",
                "description": (
                    "Get full details for a specific product by its ID. Use this when you need "
                    "detailed info about a product before adding it to the cart."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "STRING",
                            "description": "The product identifier (e.g. 'prod_rice_basmati_5kg')",
                        }
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "check_stock",
                "description": (
                    "Check whether a product is currently in stock and how many units are available. "
                    "Always check stock before adding to cart."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "STRING",
                            "description": "The product identifier",
                        }
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "add_to_cart",
                "description": (
                    "Add a product to the buyer's shopping cart. Specify the product ID and quantity. "
                    "You must check stock availability BEFORE calling this tool."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "STRING",
                            "description": "The product identifier",
                        },
                        "quantity": {
                            "type": "INTEGER",
                            "description": "Number of units to add (default: 1)",
                        },
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "view_cart",
                "description": (
                    "View the current contents of the shopping cart, including items, quantities, "
                    "subtotals, and the total amount."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {},
                },
            },
            {
                "name": "remove_from_cart",
                "description": "Remove a product from the shopping cart entirely.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "product_id": {
                            "type": "STRING",
                            "description": "The product identifier to remove",
                        }
                    },
                    "required": ["product_id"],
                },
            },
            {
                "name": "checkout",
                "description": (
                    "Finalize the cart and create a Razorpay order for payment. This runs all "
                    "policy checks (spend cap, category allowlist, price limits) and creates "
                    "the order only if all checks pass. If any check fails, the purchase is "
                    "blocked and the buyer is asked for explicit approval."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {},
                },
            },
            {
                "name": "approve_blocked_checkout",
                "description": (
                    "Explicitly approve a previously blocked checkout. Only call this after "
                    "the buyer has reviewed the block reason and confirmed they want to proceed. "
                    "This overrides the policy block for this specific transaction."
                ),
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "confirmation": {
                            "type": "STRING",
                            "description": "The buyer's confirmation message (e.g. 'yes, proceed')",
                        }
                    },
                    "required": ["confirmation"],
                },
            },
        ]
    }
]

SYSTEM_PROMPT = """You are a friendly and helpful merchant shopping assistant for "AgenticMart", an online store.

Your role:
1. Help buyers discover products from the catalog by searching and browsing
2. Build their shopping cart with the right items and quantities
3. Guide them through checkout, ensuring all policy checks pass
4. If a purchase is blocked by policy (spend cap exceeded, item too expensive, etc.), clearly explain WHY it was blocked and ask the buyer for explicit approval before proceeding

Important rules:
- Always check stock before adding items to cart
- Always show prices in Indian Rupees (₹). Prices from the catalog are in paise — divide by 100 to get rupees.
- When showing search results, format them clearly with name, price, and availability
- Before checkout, show the complete cart summary and total
- If a policy check blocks the purchase, DO NOT proceed silently — explain the block and ask for approval
- The session spend cap is ₹2,000. Inform the buyer if they're approaching or exceeding it
- Be transparent about all costs and policy decisions — this is an auditable system

You have access to the following tools:
- search_products: Search the catalog
- get_product: Get product details
- check_stock: Check availability
- add_to_cart: Add items to cart
- view_cart: View cart contents
- remove_from_cart: Remove items
- checkout: Finalize and create payment order
- approve_blocked_checkout: Override a policy block with buyer approval
"""
