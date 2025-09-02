import json

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse
from django.utils import timezone

from core.viewmodels import DashboardContext
from inventory.models import Indent, StockTransaction, Supplier
from inventory.models.enums import IndentStatus


@pytest.mark.django_db
def test_dashboard_context_basic():
    ctx = DashboardContext(labels=["2024-01-01"], values=[1])
    data = ctx.as_dict()
    assert data["trend_labels"] == json.dumps(["2024-01-01"])
    assert data["trend_values"] == json.dumps([1])
    assert data["list_title"] == "Dashboard"
    assert "items" not in data and "suppliers" not in data


@pytest.mark.django_db
def test_dashboard_low_stock(client, item_factory, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    perm = Permission.objects.get(codename="add_purchaseorder")
    user.user_permissions.add(perm)
    client.force_login(user)
    item_factory(name="Foo", reorder_point=10, current_stock=5)
    item_factory(name="Inactive", reorder_point=10, current_stock=5, is_active=False)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert b"Foo" in resp.content
    assert b"Inactive" not in resp.content


@pytest.mark.django_db
def test_dashboard_kpis_endpoint(client, item_factory):
    fresh = item_factory(name="Foo", reorder_point=10, current_stock=5)
    StockTransaction.objects.create(
        item=fresh,
        quantity_change=1,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )

    Supplier.objects.create(name="Supp")
    Indent.objects.create(mrn="1", status=IndentStatus.PENDING)

    resp = client.get(reverse("dashboard-kpis"))
    assert resp.status_code == 200
    assert b"Items" in resp.content
    assert b"Low-stock Items" in resp.content
    assert b"Suppliers" in resp.content
    assert b"Pending Indents" in resp.content

    html = resp.content.decode()
    assert f'href="{reverse("items_list")}"' in html
    assert f'href="{reverse("items_list")}?stock_status=low"' in html
    assert f'href="{reverse("suppliers_list")}"' in html
    assert f'href="{reverse("indents_list")}?status={IndentStatus.PENDING}"' in html


@pytest.mark.django_db
def test_dashboard_has_single_filter_form(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("dashboard"))
    assert resp.status_code == 200
    assert resp.content.count(b"dashboard-filters") == 1
    assert b'hx-get=""' not in resp.content
