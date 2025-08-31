import pytest

from inventory.models import Department
from inventory.services import item_service


@pytest.mark.django_db
def test_item_viewset_prefetch_departments(client, item_factory, django_assert_num_queries):
    dept = Department.objects.create(name="Kitchen")
    item1 = item_factory(name="Item1")
    item2 = item_factory(name="Item2")
    item1.departments.add(dept)
    item2.departments.add(dept)

    with django_assert_num_queries(4):
        response = client.get("/api/items/")
    assert response.status_code == 200
    data = response.json()
    assert {r["department_names"] for r in data["results"]} == {"Kitchen"}


@pytest.mark.django_db
def test_get_item_details_prefetch(item_factory, django_assert_num_queries, monkeypatch):
    item = item_factory(name="Item1")
    dept = Department.objects.create(name="Kitchen")
    item.departments.add(dept)

    monkeypatch.setattr(item_service, "get_unit_display_name", lambda unit_id: "KG")

    with django_assert_num_queries(2):
        details = item_service.get_item_details(item.item_id)
    assert details["department_names"] == "Kitchen"
