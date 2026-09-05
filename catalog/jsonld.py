"""Agent-Readable Catalog — JSON-LD / Schema.org product serialization.

Converts the merchant's product catalog into machine-readable JSON-LD
format following Schema.org's Product + Offer vocabulary. This makes
the merchant discoverable and transactable by any AI agent following
the open web standards.

Ref: https://schema.org/Product
"""

from catalog.db import get_all_products, get_product


def _product_to_jsonld(product: dict) -> dict:
    """Convert a single product dict to Schema.org JSON-LD."""
    price_rupees = product["price"] / 100
    in_stock = product.get("stock", 0) > 0

    return {
        "@context": "https://schema.org",
        "@type": "Product",
        "@id": f"https://agenticmart.razorpay.demo/products/{product['id']}",
        "productID": product["id"],
        "name": product["name"],
        "description": product.get("description", ""),
        "category": product.get("category", ""),
        "offers": {
            "@type": "Offer",
            "priceCurrency": "INR",
            "price": f"{price_rupees:.2f}",
            "priceSpecification": {
                "@type": "PriceSpecification",
                "price": price_rupees,
                "priceCurrency": "INR",
                "valueAddedTaxIncluded": True,
            },
            "availability": (
                "https://schema.org/InStock"
                if in_stock
                else "https://schema.org/OutOfStock"
            ),
            "inventoryLevel": {
                "@type": "QuantitativeValue",
                "value": product.get("stock", 0),
            },
            "seller": {
                "@type": "Organization",
                "name": "AgenticMart",
                "url": "https://agenticmart.razorpay.demo",
            },
            "acceptedPaymentMethod": {
                "@type": "PaymentMethod",
                "name": "Razorpay",
                "description": "AP2 Protocol via Razorpay Test Mode",
            },
        },
        "additionalProperty": [
            {
                "@type": "PropertyValue",
                "name": "ap2_compatible",
                "value": True,
                "description": "This product is transactable via AP2 agent-to-agent protocol",
            },
            {
                "@type": "PropertyValue",
                "name": "agent_checkout_url",
                "value": "https://agenticmart.razorpay.demo/api/chat",
                "description": "Endpoint for agent-to-agent checkout negotiation",
            },
        ],
    }


def get_catalog_jsonld() -> dict:
    """Get the full catalog as a JSON-LD ItemList."""
    products = get_all_products()
    items = [_product_to_jsonld(p) for p in products]

    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "AgenticMart Product Catalog",
        "description": "AI-agent-readable product catalog for autonomous commerce via AP2 protocol",
        "numberOfItems": len(items),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "item": item,
            }
            for i, item in enumerate(items)
        ],
        "potentialAction": {
            "@type": "SearchAction",
            "target": "https://agenticmart.razorpay.demo/api/catalog/agent-readable?q={search_term}",
            "query-input": "required name=search_term",
        },
    }


def get_product_jsonld(product_id: str) -> dict | None:
    """Get a single product as JSON-LD."""
    product = get_product(product_id)
    if not product:
        return None
    return _product_to_jsonld(product)
