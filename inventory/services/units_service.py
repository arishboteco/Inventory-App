"""
Units Service - Proper Implementation of Units Table Architecture

This service implements the correct units table logic:

1. unit_id: Unique identifier used across the application to reference units
2. base_unit: Standard unit for recipes and calculations (GM, ML, PC)
3. purchase_unit: Unit in which items are procured (2 KG, 50 GM PKT, PC)
4. conversion_factor: Numeric factor to convert purchase_unit to base_unit

Example:
- unit_id=1: base_unit=GM, purchase_unit=2 KG, conversion_factor=2000
- unit_id=19: base_unit=GM, purchase_unit=KG, conversion_factor=1000
- unit_id=55: base_unit=PC, purchase_unit=PC, conversion_factor=1

Usage:
- Items store only unit_id (foreign key reference)
- Display purchase_unit for user interface
- Use base_unit for recipe calculations
- Apply conversion_factor for unit conversions
"""

import logging
from decimal import Decimal
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from inventory.models.unit import Unit

logger = logging.getLogger(__name__)


# Mapping of human-readable unit names to unit_id for legacy compatibility.
# This supports forms that still provide unit names rather than unit_id values.
BASE_UNIT_TO_UNIT_ID = {
    "Kilograms": 19,
    "Liters": 1,
    "Pieces": 55,
    "Boxes": 55,
    "Cases": 55,
    "Cartons": 55,
    "Grams": 19,
    "Milliliters": 1,
    "Units": 55,
    "Each": 55,
    "Packages": 55,
    "Bottles": 55,
    "Cans": 55,
}


class UnitsService:
    """Service for unit conversions and display via the units table."""

    @staticmethod
    @lru_cache(maxsize=None)
    def get_unit_info(unit_id: int) -> Dict:
        """Get complete unit information for a given unit_id.

        Returns:
            dict: {
                'unit_id': int,
                'base_unit': str,
                'purchase_unit': str,
                'conversion_factor': float
            }
        """
        try:
            unit = Unit.objects.get(unit_id=unit_id)
        except Unit.DoesNotExist:
            return {
                "unit_id": unit_id,
                "base_unit": "unknown",
                "purchase_unit": "unknown",
                "conversion_factor": 1.0,
            }

        return {
            "unit_id": unit.unit_id,
            "base_unit": unit.base_unit,
            "purchase_unit": unit.purchase_unit,
            "conversion_factor": float(unit.conversion_factor),
        }

    @staticmethod
    def get_purchase_unit_display(unit_id: int) -> str:
        """Get the purchase_unit for display in UI."""
        unit_info = UnitsService.get_unit_info(unit_id)
        return unit_info["purchase_unit"]

    @staticmethod
    def get_base_unit_display(unit_id: int) -> str:
        """Get the base_unit for recipe calculations."""
        unit_info = UnitsService.get_unit_info(unit_id)
        return unit_info["base_unit"]

    @staticmethod
    def cost_per_base_for_item(item: Any) -> Decimal:
        """Cost per base unit for recipe costing (purchase price / conversion_factor).

        ``last_purchase_price`` / ``initial_purchase_price`` are per purchase_unit;
        recipe line quantities are in base_unit.
        """
        last = Decimal(str(getattr(item, "last_purchase_price", None) or 0))
        if not last:
            last = Decimal(str(getattr(item, "initial_purchase_price", None) or 0))
        unit_id = getattr(item, "unit_id", None)
        if unit_id is None:
            return last if last else Decimal("0")
        unit_info = UnitsService.get_unit_info(unit_id)
        conv = Decimal(str(unit_info.get("conversion_factor") or 1))
        if conv <= 0:
            conv = Decimal("1")
        if not last:
            return Decimal("0")
        try:
            return last / conv
        except ArithmeticError:
            return Decimal("0")

    @staticmethod
    def convert_purchase_to_base(quantity: float, unit_id: int) -> float:
        """Convert quantity from purchase_unit to base_unit.

        Used when:
        - Adding items to recipes (need base_unit amounts)
        - Calculating nutritional values
        - Standardizing measurements for reporting

        Args:
            quantity: Amount in purchase_unit (e.g., 1.5 if buying 1.5 of "2 KG" bags)
            unit_id: Reference to units table

        Returns:
            Amount in base_unit (e.g., 3000 GM for 1.5 x "2 KG" bags)
        """
        unit_info = UnitsService.get_unit_info(unit_id)
        return quantity * unit_info["conversion_factor"]

    @staticmethod
    def convert_base_to_purchase(base_quantity: float, unit_id: int) -> float:
        """Convert quantity from base_unit to purchase_unit.

        Used when:
        - Displaying stock levels in purchase units
        - Creating purchase orders
        - Showing reorder quantities

        Args:
            base_quantity: Amount in base_unit (e.g., 3000 GM)
            unit_id: Reference to units table

        Returns:
            Amount in purchase_unit (e.g., 1.5 for "2 KG" bags)
        """
        unit_info = UnitsService.get_unit_info(unit_id)
        return base_quantity / unit_info["conversion_factor"]

    @staticmethod
    @lru_cache(maxsize=None)
    def get_all_units() -> List[Dict]:
        """Get all available units for dropdown population."""
        units = Unit.objects.all().order_by("base_unit", "purchase_unit")
        return [
            {
                "unit_id": unit.unit_id,
                "base_unit": unit.base_unit,
                "purchase_unit": unit.purchase_unit,
                "conversion_factor": float(unit.conversion_factor),
            }
            for unit in units
        ]

    @staticmethod
    def get_units_by_base_unit(base_unit: str) -> List[Dict]:
        """Get all purchase units available for a given base unit."""
        all_units = UnitsService.get_all_units()
        return [unit for unit in all_units if unit["base_unit"] == base_unit]

    @staticmethod
    def get_unit_choices_for_forms() -> List[Tuple[int, str]]:
        """Get unit choices formatted for Django forms (value, label)."""
        all_units = UnitsService.get_all_units()
        return [
            (unit["unit_id"], f"{unit['purchase_unit']} ({unit['base_unit']})")
            for unit in all_units
        ]

    @staticmethod
    def validate_unit_id(unit_id: int) -> bool:
        """Check if a unit_id exists in the units table."""
        unit_info = UnitsService.get_unit_info(unit_id)
        return unit_info["base_unit"] != "unknown"


# Note: legacy convenience functions have been removed.
# Use UnitsService methods directly or item_service.get_unit_display_name.
