"""Services for recording sales transactions."""
from typing import Tuple, Optional

from . import recipe_service


def record_sale(recipe_id: int, quantity: float, user_id: str, notes: Optional[str] = None) -> Tuple[bool, str]:
    """Record a sale via :mod:`recipe_service` and adjust stock."""
    return recipe_service.record_sale(recipe_id, quantity, user_id, notes)
