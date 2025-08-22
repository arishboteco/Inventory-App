import pytest
from django.test import RequestFactory

from inventory.models import Item
from inventory.services import list_utils


@pytest.mark.django_db
def test_apply_filters_sort():
    Item.objects.create(name="Apple", category="Fruit", base_unit="kg")
    Item.objects.create(name="Banana", category="Fruit", base_unit="kg")
    Item.objects.create(name="Carrot", category="Veg", base_unit="kg")
    request = RequestFactory().get(
        "/items",
        {"q": "a", "category": "Fruit", "sort": "name", "direction": "desc"},
    )
    qs, params = list_utils.apply_filters_sort(
        request,
        Item.objects.all(),
        search_fields=["name"],
        filter_fields={"category": "category"},
        allowed_sorts={"name"},
        default_sort="name",
    )
    assert list(qs.values_list("name", flat=True)) == ["Banana", "Apple"]
    assert params["category"] == "Fruit"
    assert params["sort"] == "name"
    assert params["direction"] == "desc"


@pytest.mark.django_db
def test_paginate():
    for i in range(3):
        Item.objects.create(name=f"Item{i}", category="Cat", base_unit="kg")
    request = RequestFactory().get("/items", {"page_size": "2", "page": "2"})
    page_obj, per_page = list_utils.paginate(
        request, Item.objects.all().order_by("item_id")
    )
    assert per_page == 2
    assert list(page_obj.object_list.values_list("name", flat=True)) == ["Item2"]


@pytest.mark.django_db
def test_export_as_csv():
    Item.objects.create(name="Apple", category="Fruit", base_unit="kg")
    qs = Item.objects.all()
    response = list_utils.export_as_csv(qs, ["Name"], lambda i: [i.name], "items.csv")
    content = response.content.decode().strip().splitlines()
    assert content[0] == "Name"
    assert content[1] == "Apple"


def test_build_querystring():
    request = RequestFactory().get("/items", {"q": "x", "page": "2"})
    qs = list_utils.build_querystring(request)
    assert qs == "q=x"
