"""Database initialization and seeding."""

import sqlite3
import os
from pathlib import Path


DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "agentic_commerce.db"


def get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,          -- price in paise
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT,
            category TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            actor TEXT NOT NULL,              -- buyer / orchestrator / catalog / gate / razorpay
            action TEXT NOT NULL,
            mandate_ref TEXT,                 -- links to intent/cart/payment mandate
            amount INTEGER,                  -- amount in paise, nullable
            rule_outcome TEXT,               -- allowed / blocked / n/a
            reason TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor);
    """)
    conn.commit()


def seed_products(conn: sqlite3.Connection) -> None:
    """Seed the catalog with dummy products. Idempotent — skips if products exist."""
    cursor = conn.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  Products table already has {count} rows, skipping seed.")
        return

    from catalog.data import PRODUCTS
    conn.executemany(
        "INSERT INTO products (id, name, price, stock, description, category) VALUES (?, ?, ?, ?, ?, ?)",
        [(p["id"], p["name"], p["price"], p["stock"], p["description"], p["category"]) for p in PRODUCTS]
    )
    conn.commit()
    print(f"  Seeded {len(PRODUCTS)} products.")


def init_db() -> None:
    """Full database initialization: create tables and seed data."""
    conn = get_connection()
    try:
        print("Creating tables...")
        create_tables(conn)
        print("Seeding products...")
        seed_products(conn)
        print(f"Database ready at: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
