from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from inventory.forms.purchase_forms import PurchaseOrderForm
from inventory.forms.recovery_forms import (
    RecoveryActionStatusForm,
    SavingsLedgerForm,
)
from inventory.models import PurchaseOrder, Recipe, SaleTransaction, Supplier

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_client(client, django_user_model):
    owner_group, _ = Group.objects.get_or_create(name="Owner")
    owner = django_user_model.objects.create_user(
        username="phase10_owner",
        password="pw12345",
        is_staff=True,
    )
    owner.groups.add(owner_group)
    client.force_login(owner)
    return client


@pytest.fixture
def phase10_base_data(item_factory):
    supplier = Supplier.objects.create(name="Phase10 Supplier", is_active=True)
    item = item_factory(name="Phase10 Chicken", current_stock=Decimal("20.00"))
    recipe = Recipe.objects.create(
        name="Phase10 Recipe",
        type=Recipe.Type.FINAL,
        is_active=True,
        selling_price=Decimal("280.00"),
        target_food_cost_pct=Decimal("32.00"),
    )
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("10.00"),
        sale_date=date.today(),
        outlet="Main Outlet",
        pos_item_name=recipe.name,
        gross_sales=Decimal("2800.00"),
        discount=Decimal("140.00"),
        net_sales=Decimal("2660.00"),
        tax=Decimal("133.00"),
        source=SaleTransaction.Source.POS_CSV,
        notes="Phase10 smoke seed",
    )
    PurchaseOrder.objects.create(
        supplier=supplier,
        order_date=date.today(),
        status="DRAFT",
    )
    return {"supplier": supplier, "item": item, "recipe": recipe}


@pytest.mark.parametrize(
    "url_name",
    [
        "root",
        "items_list",
        "suppliers_list",
        "recipes_list",
        "indents_list",
        "purchase_orders_list",
        "grn_list",
        "stock_movements",
        "savings_ledger_list",
        "vendor_prices_list",
        "pos_sales_import",
        "variance_report",
        "chef_bulletins_list",
        "recovery_actions_list",
        "settings",
    ],
)
def test_phase10_owner_pages_render(owner_client, phase10_base_data, url_name):
    response = owner_client.get(reverse(url_name))
    assert response.status_code == 200


def test_phase10_purchase_order_form_accepts_manual_date(supplier_factory):
    supplier = supplier_factory(name="Phase10 PO Supplier")
    form = PurchaseOrderForm(
        data={
            "supplier": str(supplier.pk),
            "order_date": "22/05/2026",
            "expected_delivery_date": "25/05/2026",
            "status": "DRAFT",
            "notes": "manual date entry",
        }
    )
    assert form.is_valid(), form.errors


def test_phase10_savings_form_accepts_manual_date(item_factory):
    item = item_factory(name="Phase10 Ledger Item")
    form = SavingsLedgerForm(
        data={
            "date": "22-05-2026",
            "item": item.pk,
            "saving_type": "WASTE_REDUCTION",
            "source_document_type": "Manual",
            "source_document_id": "P10-001",
            "baseline_price": "0",
            "selected_price": "0",
            "invoice_price": "0",
            "quantity": "0",
            "estimated_saving": "40",
            "confirmed_saving": "0",
            "lost_saving": "0",
            "status": "ESTIMATED",
            "notes": "manual date entry",
        }
    )
    assert form.is_valid(), form.errors


def test_phase10_status_form_accepts_manual_date():
    form = RecoveryActionStatusForm(
        data={
            "status": "IMPLEMENTED",
            "verified_saving": "",
            "implemented_date": "22/05/2026",
            "notes": "implemented",
        }
    )
    assert form.is_valid(), form.errors
