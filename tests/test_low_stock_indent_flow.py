import pytest
from django.urls import reverse
from django.utils import timezone

from inventory.models import Indent, IndentItem


@pytest.mark.django_db
def test_low_stock_indent_post_creates_indent_and_items(client, item_factory):
    item_factory(
        name="Chicken",
        reorder_point=1000,
        current_stock=50,
        minimum_order_qty=0,
        unit_id=19,
        category_id=1,
        is_active=True,
    )

    url = reverse("low_stock_indent")
    response = client.post(url, follow=True)

    assert response.redirect_chain
    assert response.status_code == 200

    indent = Indent.objects.get()
    assert response.request["PATH_INFO"] == reverse(
        "indent_detail", kwargs={"pk": indent.pk}
    )
    item_lines = IndentItem.objects.filter(indent=indent)
    assert item_lines.count() == 1
    assert float(item_lines.first().requested_qty) == 950.0


@pytest.mark.django_db
def test_low_stock_indent_post_uses_unique_mrn_within_same_second(
    client, item_factory, monkeypatch
):
    item_factory(
        name="Chicken",
        reorder_point=1000,
        current_stock=50,
        minimum_order_qty=0,
        unit_id=19,
        category_id=1,
        is_active=True,
    )

    fixed_now = timezone.now().replace(microsecond=0)
    monkeypatch.setattr("inventory.views.indents.timezone.now", lambda: fixed_now)

    url = reverse("low_stock_indent")
    first = client.post(url)
    second = client.post(url)

    assert first.status_code == 302
    assert second.status_code == 302
    assert Indent.objects.count() == 2
