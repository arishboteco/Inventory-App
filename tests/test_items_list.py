from datetime import date
from decimal import Decimal

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import (
    Department,
    Item,
    PurchaseOrder,
    PurchaseOrderItem,
    StockTransaction,
    Supplier,
)


def _create_item(**kwargs):
    defaults = {
        "name": "Widget",
        "unit_id": 55,
        "reorder_point": 1,
        "notes": "n",
        "is_active": True,
        "category_id": 1,
    }
    defaults.update(kwargs)
    return Item.objects.create(**defaults)


@pytest.mark.django_db
def test_reorder_point_displayed_when_set(client):
    _create_item(current_stock=Decimal("5"), reorder_point=Decimal("3"))
    resp = client.get(reverse("items_table"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    cell = soup.find("td", {"data-col": "stock_status"})
    assert "Reorder Point: 3" in cell.get_text()


@pytest.mark.django_db
def test_reorder_point_absent_when_unset(client):
    _create_item(current_stock=Decimal("5"), reorder_point=0)
    resp = client.get(reverse("items_table"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    cell = soup.find("td", {"data-col": "stock_status"})
    assert "Reorder Point" not in cell.get_text()


def test_item_link_in_table_layout(client):
    item = _create_item()
    resp = client.get(reverse("items_table"))
    assert resp.status_code == 200
    assert reverse("item_detail", args=[item.pk]) in resp.content.decode()


def test_archive_action_toggles_item(client):
    item = _create_item()
    detail_url = reverse("item_detail", args=[item.pk])
    resp = client.get(detail_url)

    toggle_url = reverse("item_toggle_active", args=[item.pk])
    html = resp.content.decode()
    assert f'action="{toggle_url}"' in html
    assert 'method="post"' in html

    client.post(toggle_url)
    item.refresh_from_db()
    assert item.is_active is False

    client.post(toggle_url)
    item.refresh_from_db()
    assert item.is_active is True


def test_item_detail_includes_supplier_and_movements(client):
    item = _create_item()
    supplier = Supplier.objects.create(name="Acme Corp")
    po = PurchaseOrder.objects.create(supplier=supplier, order_date=date.today())
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=1,
        unit_price=Decimal("1.00"),
    )
    tx = StockTransaction.objects.create(
        item=item, quantity_change=Decimal("5"), transaction_type="IN"
    )
    resp = client.get(reverse("item_detail", args=[item.pk]))
    content = resp.content.decode()
    assert supplier.name in content
    assert tx.transaction_type in content
    assert str(tx.quantity_change) in content
    assert (
        '<h2 class="text-h2 md:text-h3 font-semibold">Supplier History</h2>' in content
    )
    assert (
        '<h2 class="text-h2 md:text-h3 font-semibold">Stock Movements</h2>' in content
    )


@pytest.mark.django_db
def test_items_list_kpis_displayed(client):
    _create_item(last_purchase_price=Decimal("1.00"))
    resp = client.get(reverse("items_list"))
    assert resp.status_code == 200
    html = resp.content.decode()
    assert "Active Items" in html
    assert "Low Stock %" in html
    assert "Avg Days Since Purchase" in html
    assert "Stock Value" in html


@pytest.mark.django_db
def test_items_toolbar_structure(client):
    _create_item()
    resp = client.get(reverse("items_list"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    toolbar = soup.find(id="items-toolbar")
    assert toolbar is not None
    # Ensure search/filter form is present on the left
    filters_form = toolbar.find("form", id="filters")
    assert filters_form is not None
    # Ensure action buttons are present on the right
    add_btn = toolbar.find(
        "button",
        {
            "data-modal-url": reverse("item_create_partial"),
            "data-modal-type": "drawer",
        },
    )
    bulk_btn = toolbar.find(
        "button",
        {
            "data-modal-url": reverse("items_bulk_upload") + "?partial=1",
            "data-modal-type": "drawer",
        },
    )
    export_btn = toolbar.find(
        "button", {"form": "filters", "formaction": reverse("items_export")}
    )
    assert add_btn is not None
    assert bulk_btn is not None
    assert export_btn is not None
    # Collapsible sections should not be present anymore
    assert soup.find(id="add-item-section") is None
    assert soup.find(id="bulk-upload-section") is None


@pytest.mark.django_db
def test_item_create_partial_departments_multiselect_container(client):
    Department.objects.create(name="Kitchen")
    resp = client.get(reverse("item_create_partial"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    root_div = soup.find(
        "div",
        class_="bg-white rounded-xl shadow border border-gray-200 overflow-hidden drawer-panel max-w-drawer-xl",
    )
    assert root_div is not None
    container = soup.find("div", {"data-multiselect": "chips"})
    assert container is not None
    classes = container.get("class", [])
    assert "grid" in classes
    checkboxes = container.find_all("input", {"type": "checkbox"})
    assert len(checkboxes) >= 1


@pytest.mark.django_db
def test_filters_persist_after_table_refresh(client):
    """Filters should remain visible after HTMX table updates."""
    _create_item()
    # Initial page load contains the filter bar
    resp = client.get(reverse("items_list"))
    assert resp.status_code == 200
    initial_html = resp.content.decode()
    assert 'id="items-filter-bar"' in initial_html

    # Simulate an HTMX request to refresh the table
    table_resp = client.get(reverse("items_table"), HTTP_HX_REQUEST="true")
    assert table_resp.status_code == 200
    table_html = table_resp.content.decode()

    # The table partial should not contain the filter bar
    assert "items-filter-bar" not in table_html


@pytest.mark.django_db
def test_drawer_width(client):
    resp = client.get(reverse("item_create_partial"))
    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content, "html.parser")
    drawer = soup.find("div", class_="drawer-panel")
    assert drawer is not None
    assert "max-w-drawer-xl" in drawer.get("class")
