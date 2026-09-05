"""Catalog MCP server — exposes product tools via Model Context Protocol."""

import json
from mcp.server.fastmcp import FastMCP
from catalog.db import search_products, get_product, check_stock


# Initialize MCP server
mcp = FastMCP("ProductCatalog")


@mcp.tool()
def search_catalog(query: str) -> str:
    """
    Search the product catalog by keyword. Matches against product name,
    description, and category. Returns a JSON array of matching products
    with id, name, price (in paise), stock, description, and category.

    Args:
        query: Search term (e.g. "snacks", "rice", "electronics")
    """
    results = search_products(query)
    if not results:
        return json.dumps({"results": [], "message": f"No products found for '{query}'"})
    return json.dumps({"results": results, "count": len(results)})


@mcp.tool()
def get_product_details(product_id: str) -> str:
    """
    Get full details for a specific product by its ID.

    Args:
        product_id: The product identifier (e.g. "prod_rice_basmati_5kg")
    """
    product = get_product(product_id)
    if product is None:
        return json.dumps({"error": f"Product '{product_id}' not found"})
    return json.dumps(product)


@mcp.tool()
def check_product_stock(product_id: str) -> str:
    """
    Check whether a product is in stock and how many units are available.

    Args:
        product_id: The product identifier (e.g. "prod_bt_earbuds")
    """
    stock_info = check_stock(product_id)
    if stock_info is None:
        return json.dumps({"error": f"Product '{product_id}' not found"})
    return json.dumps(stock_info)


if __name__ == "__main__":
    import sys
    import os

    # Ensure project root is on the path so imports work
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Initialize the database before starting the server
    from db.setup import init_db
    init_db()

    print("Starting ProductCatalog MCP server on http://localhost:8001/mcp")
    mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)
