import pytest
from django.urls import reverse

from inventory.models import Category, Item, Unit


@pytest.mark.django_db
def test_distinct_unit_respects_category_filter(client):
    unit1 = Unit.objects.create(purchase_unit="kg", base_unit="kg", conversion_factor=1)
    unit2 = Unit.objects.create(purchase_unit="l", base_unit="l", conversion_factor=1)
    cat1 = Category.objects.create(category="Food", sub_category="Spices")
    cat2 = Category.objects.create(category="Drink", sub_category="Juice")
    Item.objects.create(
        name="Sugar",
        unit=unit1,
        category=cat1,
        reorder_point=1,
        notes="n",
        is_active=True,
    )
    Item.objects.create(
        name="Milk",
        unit=unit2,
        category=cat2,
        reorder_point=1,
        notes="n",
        is_active=True,
    )

    url = reverse("items_distinct", args=["unit"])
    resp = client.get(url, {"category": "Food"})
    assert resp.status_code == 200
    assert resp.json() == [{"value": "kg", "label": "kg"}]


@pytest.mark.django_db
def test_distinct_pagination(client):
    cat = Category.objects.create(category="Cat", sub_category="Sub")
    units = [
        Unit.objects.create(
            purchase_unit=f"u{i}", base_unit=f"u{i}", conversion_factor=1
        )
        for i in range(5)
    ]
    for idx, u in enumerate(units):
        Item.objects.create(
            name=f"Item {idx}",
            unit=u,
            category=cat,
            reorder_point=1,
            notes="n",
            is_active=True,
        )
    url = reverse("items_distinct", args=["unit"])
    resp1 = client.get(url, {"limit": 2, "page": 1})
    resp2 = client.get(url, {"limit": 2, "page": 2})
    resp3 = client.get(url, {"limit": 2, "page": 3})
    assert len(resp1.json()) == 2
    assert len(resp2.json()) == 2
    assert len(resp3.json()) == 1
