"""
Authenticated GET smoke tests for inventory UI URL names.

Exercises nearly every named route in inventory/ui_urls.py with a logged-in user
and minimal DB rows so detail URLs resolve. Catches broken links (404/500) and
auth walls (302 to login) for normal navigation.

POST-only endpoints are skipped for GET (405 is acceptable but not asserted here).
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.urls import NoReverseMatch, reverse

from inventory.models import (
    GoodsReceivedNote,
    Indent,
    PurchaseOrder,
    PurchaseOrderItem,
    Recipe,
    StockTake,
    StockTakeItem,
    Supplier,
)
from inventory.models.enums import IndentStatus

pytestmark = pytest.mark.django_db

# Named routes that only accept POST (no meaningful GET for "link" checks).
_POST_ONLY_GET_SKIP = frozenset(
    {
        "item_create",
        "items_bulk_update",
        "indent_update",
        "indent_update_status",
        "indents_consolidate",
        "purchase_order_mark_ordered",
        "item_inline_update",
        "supplier_delete",
        "suppliers_bulk_delete",
        "recipe_create_indent",
    }
)


@pytest.fixture
def smoke_entities(item_factory, django_user_model):
    """Minimal related rows so pk-based URLs reverse and resolve."""
    supplier = Supplier.objects.create(name=f"SmokeSup-{uuid.uuid4().hex[:6]}")
    item = item_factory(name=f"SmokeItem-{uuid.uuid4().hex[:6]}")
    recipe = Recipe.objects.create(
        name=f"SmokeRec-{uuid.uuid4().hex[:6]}",
        type=Recipe.Type.FINAL,
        is_active=True,
    )
    indent = Indent.objects.create(
        mrn=f"MRN-{uuid.uuid4().hex[:8]}",
        status=IndentStatus.SUBMITTED,
    )
    po = PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="SENT",
    )
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        item=item,
        quantity_ordered=Decimal("10"),
        unit_price=Decimal("1.00"),
    )
    grn = GoodsReceivedNote.objects.create(
        supplier=supplier,
        received_date=date.today(),
        purchase_order=po,
    )
    user = django_user_model.objects.get(username="admin")
    stock_take = StockTake.objects.create(
        date=date.today(),
        status="IN_PROGRESS",
        created_by=user,
        notes="smoke",
    )
    StockTakeItem.objects.create(
        stock_take=stock_take,
        item=item,
        system_qty=Decimal("0"),
    )
    return {
        "item": item,
        "supplier": supplier,
        "recipe": recipe,
        "indent": indent,
        "po": po,
        "grn": grn,
        "stock_take": stock_take,
    }


def _kwargs_for_url_name(name: str, ctx: dict) -> dict | None:
    """Return kwargs for reverse(), or None if this test uses query string only."""
    item = ctx["item"]
    supplier = ctx["supplier"]
    recipe = ctx["recipe"]
    indent = ctx["indent"]
    po = ctx["po"]
    grn = ctx["grn"]
    stock_take = ctx["stock_take"]

    pk_urls = {
        "item_edit": {"pk": item.pk},
        "item_delete": {"pk": item.pk},
        "item_toggle_active": {"pk": item.pk},
        "item_detail": {"pk": item.pk},
        "item_meta": {"item_id": item.pk},
        "supplier_edit": {"pk": supplier.pk},
        "supplier_toggle_active": {"pk": supplier.pk},
        "supplier_detail": {"pk": supplier.pk},
        "stock_take_count": {"pk": stock_take.pk},
        "stock_take_review": {"pk": stock_take.pk},
        "indent_detail": {"pk": indent.pk},
        "indent_update": {"pk": indent.pk},
        "issue_indent": {"pk": indent.pk},
        "indent_pdf": {"pk": indent.pk},
        "indent_update_status": {"pk": indent.pk, "status": "APPROVED"},
        "purchase_order_edit": {"pk": po.pk},
        "purchase_order_edit_partial": {"pk": po.pk},
        "purchase_order_mark_ordered": {"pk": po.pk},
        "purchase_order_detail": {"pk": po.pk},
        "purchase_order_receive": {"pk": po.pk},
        "purchase_order_receive_partial": {"pk": po.pk},
        "grn_export": {"pk": grn.pk},
        "grn_detail": {"pk": grn.pk},
        "recipe_meta": {"recipe_id": recipe.pk},
        "recipe_edit_partial": {"pk": recipe.pk},
        "recipe_view_partial": {"pk": recipe.pk},
        "recipe_delete": {"pk": recipe.pk},
        "recipe_detail": {"pk": recipe.pk},
        "recipe_create_indent": {"pk": recipe.pk},
    }
    if name in pk_urls:
        return pk_urls[name]

    if name == "items_distinct":
        return {"field": "name"}

    return {}


def _get_querystring(name: str) -> str:
    # Full-page GET is intentionally 404; drawer loads this URL with partial=1.
    if name == "indent_create":
        return "?partial=1"
    if name == "item_search":
        return "?q=a"
    if name in ("supplier_search", "user_search", "po_search"):
        return "?q="
    if name == "recipe_meta":
        return "?q="
    return ""


_UI_URL_NAMES: tuple[str, ...] = (
    "explore",
    "explore_export",
    "items_list",
    "items_table",
    "items_export",
    "items_distinct",
    "item_create_partial",
    "item_create",
    "item_inline_update",
    "items_bulk_update",
    "upload_csv",
    "item_edit",
    "item_delete",
    "item_toggle_active",
    "item_detail",
    "item_search",
    "item_meta",
    "get_purchase_units",
    "get_subcategories",
    "items_bulk_upload",
    "suppliers_list",
    "suppliers_table",
    "suppliers_cards",
    "supplier_create",
    "supplier_edit",
    "supplier_toggle_active",
    "suppliers_bulk_upload",
    "suppliers_bulk_upload_partial",
    "suppliers_bulk_delete",
    "supplier_search",
    "supplier_detail",
    "supplier_delete",
    "stock_movements",
    "user_search",
    "po_search",
    "history_reports",
    "stock_take_list",
    "stock_take_start",
    "stock_take_count",
    "stock_take_review",
    "visualizations",
    "indents_list",
    "indents_table",
    "indent_create",
    "indent_detail",
    "indent_update",
    "issue_indent",
    "indent_update_status",
    "indent_pdf",
    "low_stock_indent",
    "indents_consolidate",
    "indents_consolidate_preview",
    "purchase_orders_list",
    "purchase_orders_table",
    "purchase_orders_cards",
    "purchase_orders_export",
    "purchase_order_create",
    "purchase_order_create_partial",
    "purchase_order_edit",
    "purchase_order_edit_partial",
    "purchase_order_mark_ordered",
    "purchase_order_detail",
    "purchase_order_receive",
    "purchase_order_receive_partial",
    "grn_list",
    "grn_create",
    "grn_create_adhoc",
    "grn_export",
    "grn_detail",
    "recipes_list",
    "recipes_table",
    "food_cost_report",
    "recipe_meta",
    "recipe_create",
    "recipe_create_partial",
    "ml_dashboard",
    "recipe_edit_partial",
    "recipe_view_partial",
    "recipe_create_indent",
    "recipe_delete",
    "recipe_detail",
    "workflow_guide",
    "settings",
    "profile-edit",
    "change-password",
)


@pytest.mark.parametrize("url_name", _UI_URL_NAMES)
def test_ui_url_get_smoke(client, smoke_entities, url_name: str):
    if url_name in _POST_ONLY_GET_SKIP:
        pytest.skip("POST-only endpoint")

    kwargs = _kwargs_for_url_name(url_name, smoke_entities)
    if kwargs is None:
        kwargs = {}

    try:
        path = reverse(url_name, kwargs=kwargs)
    except NoReverseMatch as e:
        pytest.fail(f"reverse({url_name!r}, {kwargs!r}) failed: {e}")

    path = path + _get_querystring(url_name)
    resp = client.get(path)
    assert resp.status_code in (
        200,
        301,
        302,
    ), f"{url_name} GET {path!r} returned {resp.status_code}"
    if resp.status_code == 302:
        loc = resp.get("Location", "")
        assert (
            "/accounts/login/" not in loc
        ), f"{url_name} redirected to login — possible auth hole for {path!r}"


@pytest.mark.django_db
def test_root_dashboard_get_smoke(client):
    """Core app entry (not in inventory/ui_urls)."""
    resp = client.get(reverse("root"))
    assert resp.status_code == 200
