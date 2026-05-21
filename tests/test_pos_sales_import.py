from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from inventory.models import (
    POSMenuItemMapping,
    Recipe,
    SaleTransaction,
    StockTransaction,
)
from inventory.services import dashboard_kpis as dkpis
from inventory.services import pos_sales_import_service


def _csv_file(rows):
    header = (
        "date,outlet,pos_item_name,quantity_sold,gross_sales,discount,net_sales,tax\n"
    )
    content = header + "\n".join(rows) + "\n"
    return SimpleUploadedFile(
        "pos_sales.csv",
        content.encode("utf-8"),
        content_type="text/csv",
    )


@pytest.mark.django_db
def test_import_pos_sales_csv_stores_mapped_and_unmapped_rows():
    recipe = Recipe.objects.create(
        name="Paneer Tikka",
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("300.00"),
    )
    POSMenuItemMapping.objects.create(
        pos_item_name="Paneer Tikka POS",
        recipe=recipe,
        is_active=True,
    )
    file_obj = _csv_file(
        [
            "2026-05-20,Main,Paneer Tikka POS,2,700,50,650,30",
            "2026-05-20,Main,Unknown POS Item,1,300,0,300,15",
        ]
    )
    result = pos_sales_import_service.import_pos_sales_csv(
        file_obj,
        SimpleNamespace(username="owner"),
    )

    assert result["imported_count"] == 2
    assert result["unmapped_count"] == 1
    assert result["error_count"] == 0
    assert result["total_net_sales"] == Decimal("950")

    mapped = SaleTransaction.objects.get(pos_item_name="Paneer Tikka POS")
    unmapped = SaleTransaction.objects.get(pos_item_name="Unknown POS Item")
    assert mapped.recipe_id == recipe.recipe_id
    assert mapped.net_sales == Decimal("650")
    assert mapped.source == SaleTransaction.Source.POS_CSV
    assert mapped.source_row_number == 2
    assert unmapped.recipe is None
    assert not StockTransaction.objects.filter(transaction_type="SALE").exists()


@pytest.mark.django_db
def test_import_pos_sales_csv_collects_row_errors():
    file_obj = _csv_file(
        [
            "2026-05-20,Main,Chicken POS,0,700,50,650,30",
            "2026-05-20,Main,Chicken POS,abc,700,50,650,30",
        ]
    )
    result = pos_sales_import_service.import_pos_sales_csv(
        file_obj,
        SimpleNamespace(username="owner"),
    )

    assert result["imported_count"] == 0
    assert result["error_count"] == 2
    assert len(result["errors"]) == 2
    assert SaleTransaction.objects.count() == 0


@pytest.mark.django_db
def test_apply_mapping_updates_existing_unmapped_rows():
    recipe = Recipe.objects.create(
        name="Chicken Biryani",
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("320.00"),
    )
    sale = SaleTransaction.objects.create(
        pos_item_name="Chicken Biryani POS",
        quantity=Decimal("3"),
        net_sales=Decimal("930"),
        source=SaleTransaction.Source.POS_CSV,
    )
    mapping = POSMenuItemMapping.objects.create(
        pos_item_name="Chicken Biryani POS",
        recipe=recipe,
        is_active=True,
    )

    updated = pos_sales_import_service.apply_mapping_to_unmapped_sales(mapping)
    sale.refresh_from_db()

    assert updated == 1
    assert sale.recipe_id == recipe.recipe_id


@pytest.mark.django_db
def test_dashboard_sales_revenue_prefers_net_sales_fallback_to_recipe_price():
    recipe = Recipe.objects.create(
        name="Noodles",
        is_active=True,
        type=Recipe.Type.FINAL,
        selling_price=Decimal("100.00"),
    )
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("2"),
        net_sales=Decimal("150"),
        source=SaleTransaction.Source.POS_CSV,
    )
    SaleTransaction.objects.create(
        recipe=recipe,
        quantity=Decimal("1"),
        source=SaleTransaction.Source.MANUAL,
    )
    today = SaleTransaction.objects.latest("sale_id").sale_date.date()

    revenue = dkpis.sales_revenue(today, today)

    assert revenue == Decimal("250")


@pytest.mark.django_db
def test_pos_sales_import_page_renders_for_authenticated_user(client, django_user_model):
    user = django_user_model.objects.create_user(username="owner", password="pw")
    client.force_login(user)

    response = client.get(reverse("pos_sales_import"))

    assert response.status_code == 200
    assert "POS Sales Import" in response.content.decode()
