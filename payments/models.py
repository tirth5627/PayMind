"""Data models for payments and cart."""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class CartItem:
    """A single item in the shopping cart."""
    product_id: str
    name: str
    price: int  # paise
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.price * self.quantity

    def to_dict(self) -> dict:
        return {
            "product_id": self.product_id,
            "name": self.name,
            "price": self.price,
            "price_display": f"₹{self.price / 100:.2f}",
            "quantity": self.quantity,
            "subtotal": self.subtotal,
            "subtotal_display": f"₹{self.subtotal / 100:.2f}",
        }


@dataclass
class Order:
    """Represents a Razorpay order."""
    id: str
    amount: int  # paise
    currency: str
    status: str
    receipt: str
    created_at: float = field(default_factory=time.time)
    razorpay_order_id: Optional[str] = None
    notes: dict = field(default_factory=dict)

    @property
    def amount_display(self) -> str:
        return f"₹{self.amount / 100:.2f}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "amount": self.amount,
            "amount_display": self.amount_display,
            "currency": self.currency,
            "status": self.status,
            "receipt": self.receipt,
            "razorpay_order_id": self.razorpay_order_id,
            "created_at": self.created_at,
        }
