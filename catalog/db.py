"""Catalog database helpers — queries against the products table."""

from db.setup import get_connection
from audit.logger import log_event


def get_all_products() -> list[dict]:
    """Get all products from the catalog."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, price, stock, description, category FROM products"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def search_products(query: str) -> list[dict]:
    """Search products by name, description, or category. Returns matching products."""
    conn = get_connection()
    try:
        # Simple LIKE search — good enough for 10 products
        search_term = f"%{query}%"
        cursor = conn.execute(
            """SELECT id, name, price, stock, description, category
               FROM products
               WHERE name LIKE ? OR description LIKE ? OR category LIKE ?""",
            (search_term, search_term, search_term),
        )
        results = [dict(row) for row in cursor.fetchall()]

        log_event(
            actor="catalog",
            action="search_products",
            reason=f"Search query: '{query}' — found {len(results)} result(s)",
        )

        return results
    finally:
        conn.close()


def get_product(product_id: str) -> dict | None:
    """Get a single product by ID. Returns None if not found."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, price, stock, description, category FROM products WHERE id = ?",
            (product_id,),
        )
        row = cursor.fetchone()
        result = dict(row) if row else None

        log_event(
            actor="catalog",
            action="get_product",
            reason=f"Looked up product '{product_id}' — {'found' if result else 'not found'}",
        )

        return result
    finally:
        conn.close()


def check_stock(product_id: str) -> dict | None:
    """Check stock for a product. Returns id, name, stock count, and in_stock bool."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, name, stock FROM products WHERE id = ?",
            (product_id,),
        )
        row = cursor.fetchone()
        if row is None:
            log_event(
                actor="catalog",
                action="check_stock",
                reason=f"Stock check for '{product_id}' — product not found",
            )
            return None

        result = {
            "id": row["id"],
            "name": row["name"],
            "stock": row["stock"],
            "in_stock": row["stock"] > 0,
        }

        log_event(
            actor="catalog",
            action="check_stock",
            reason=f"Stock check for '{row['name']}': {row['stock']} units ({'in stock' if result['in_stock'] else 'OUT OF STOCK'})",
        )

        return result
    finally:
        conn.close()
