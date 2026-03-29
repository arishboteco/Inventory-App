"""Recipe total cost must use purchase-unit price / conversion (same as recipe drawer)."""

from decimal import Decimal

import pytest

from inventory.models import Item, Recipe, RecipeItem
from inventory.services.units_service import UnitsService

pytestmark = pytest.mark.django_db


def test_get_total_cost_divides_by_conversion_factor():
    """Unit 19 in test schema: KG purchase, GM base, factor 1000."""
    UnitsService.get_unit_info.cache_clear()
    item = Item.objects.create(
        name="Flour Cost Test",
        unit_id=19,
        category_id=1,
        reorder_point=0,
        current_stock=0,
        is_active=True,
        last_purchase_price=Decimal("1000.00"),
    )
    recipe = Recipe.objects.create(
        name="Recipe Cost Conversion Test",
        is_active=True,
        type=Recipe.Type.FINAL,
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("500"),
        unit="GM",
        loss_pct=Decimal("0"),
    )
    # 1000 per KG → 1 per GM → 500 GM → 500
    assert recipe.get_total_cost() == Decimal("500")
    row = RecipeItem.objects.get(recipe=recipe)
    assert row.get_line_cost() == Decimal("500")


def test_get_total_cost_conversion_factor_one():
    """Unit 55: PC base, factor 1 — cost equals price × qty."""
    UnitsService.get_unit_info.cache_clear()
    item = Item.objects.create(
        name="Bun Cost Test",
        unit_id=55,
        category_id=1,
        reorder_point=0,
        current_stock=0,
        is_active=True,
        last_purchase_price=Decimal("2.50"),
    )
    recipe = Recipe.objects.create(
        name="Recipe PC Unit Cost Test",
        is_active=True,
        type=Recipe.Type.FINAL,
    )
    RecipeItem.objects.create(
        recipe=recipe,
        item=item,
        quantity=Decimal("4"),
        unit="PC",
        loss_pct=Decimal("0"),
    )
    assert recipe.get_total_cost() == Decimal("10")
    assert RecipeItem.objects.get(recipe=recipe).get_line_cost() == Decimal("10")
