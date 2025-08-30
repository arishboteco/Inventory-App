"""Constants used across the inventory application."""

from enum import Enum


PLACEHOLDER_SELECT_COMPONENT = "-- Select Component --"


class TransactionType(str, Enum):
    """Allowed stock transaction types."""

    RECEIVING = "RECEIVING"
    ADJUSTMENT = "ADJUSTMENT"
    WASTAGE = "WASTAGE"
    SALE = "SALE"
    ISSUE = "ISSUE"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Return Django-compatible choices."""
        return [(t.value, t.value) for t in cls]


__all__ = ["PLACEHOLDER_SELECT_COMPONENT", "TransactionType"]
