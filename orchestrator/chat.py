"""Terminal chat REPL — human buyer interface for the orchestrator agent."""

import sys
import os

# Fix Windows terminal encoding for ₹ symbol and other Unicode
os.environ["PYTHONIOENCODING"] = "utf-8"
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass  # Python < 3.7

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from db.setup import init_db
from orchestrator.agent import OrchestratorAgent


BANNER = """
╔══════════════════════════════════════════════════════════════╗
║              🛒  AgenticMart — Shopping Assistant            ║
║──────────────────────────────────────────────────────────────║
║  Powered by Claude + Razorpay (test mode)                    ║
║  Session spend cap: ₹2,000                                   ║
║                                                              ║
║  Commands:                                                   ║
║    Type naturally to shop (e.g. "show me snacks")            ║
║    Type 'quit' or 'exit' to end the session                  ║
║    Type 'audit' to see recent audit log entries              ║
╚══════════════════════════════════════════════════════════════╝
"""


def show_audit_log():
    """Display recent audit log entries."""
    from audit.db import get_recent_events
    events = get_recent_events(20)
    if not events:
        print("\n  (No audit log entries yet)\n")
        return

    print("\n┌─────────────────────────────── Audit Log ───────────────────────────────┐")
    for event in reversed(events):  # Show oldest first
        ts = event.get("timestamp", "?")
        actor = event.get("actor", "?").ljust(13)
        action = event.get("action", "?").ljust(25)
        outcome = event.get("rule_outcome", "n/a").ljust(7)
        reason = event.get("reason", "")
        amount_str = ""
        if event.get("amount"):
            amount_str = f" [₹{event['amount'] / 100:.2f}]"

        print(f"  {ts} | {actor} | {action} | {outcome} |{amount_str} {reason[:80]}")
    print("└────────────────────────────────────────────────────────────────────────┘\n")


def main():
    """Run the interactive chat loop."""
    # Initialize database
    print("Initializing database...")
    init_db()
    print()

    # Initialize the agent
    print("Connecting to Claude...")
    try:
        agent = OrchestratorAgent()
    except RuntimeError as e:
        print(f"\n❌ Error: {e}")
        print("Please set your API keys in the .env file and try again.")
        sys.exit(1)

    print(BANNER)

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye! 👋")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("\nGoodbye! 👋 Thanks for shopping at AgenticMart.")
            break

        if user_input.lower() == "audit":
            show_audit_log()
            continue

        try:
            print("\n🤖 Thinking...\n")
            response = agent.chat(user_input)
            print(f"Assistant: {response}\n")
        except Exception as e:
            print(f"\n❌ Error: {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    main()
