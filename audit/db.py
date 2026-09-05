"""Audit log database helpers."""

import sqlite3
from typing import Optional
from db.setup import get_connection


def insert_event(
    actor: str,
    action: str,
    reason: str,
    mandate_ref: Optional[str] = None,
    amount: Optional[int] = None,
    rule_outcome: str = "n/a",
) -> int:
    """Insert an audit log entry. Returns the row id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO audit_log (actor, action, mandate_ref, amount, rule_outcome, reason)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (actor, action, mandate_ref, amount, rule_outcome, reason),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def clear_audit_log():
    """Clear all audit log entries."""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM audit_log")
        conn.commit()
    finally:
        conn.close()


def get_recent_events(n: int = 50) -> list[dict]:
    """Get the most recent N audit log entries."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (n,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_events_by_mandate(mandate_ref: str) -> list[dict]:
    """Get all audit log entries for a specific mandate reference."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT * FROM audit_log WHERE mandate_ref = ? ORDER BY id ASC",
            (mandate_ref,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
