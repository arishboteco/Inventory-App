import pytest
from django.urls import reverse

from inventory.models import Category, Item, Unit


@pytest.mark.django_db
def test_category_filter_updates_table(client):
    unit = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    cat1 = Category.objects.create(category="Food", sub_category="Spices")
    cat2 = Category.objects.create(category="Food", sub_category="Dairy")
    Item.objects.create(
        name="Sugar",
        unit=unit,
        category=cat1,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    Item.objects.create(
        name="Milk",
        unit=unit,
        category=cat2,
        reorder_point=1,
        notes="n",
        is_active=True,
    )

    resp = client.get(reverse("items_table"), {"subcategory": "Spices"})
    html = resp.content.decode()
    assert "Sugar" in html
    assert "Milk" not in html
