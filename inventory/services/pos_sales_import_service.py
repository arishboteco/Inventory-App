from __future__ import annotations

import csv
import io
from datetime import datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from inventory.models import POSMenuItemMapping, SaleTransaction

EXPECTED_COLUMNS = {
    "date",
    "outlet",
    "pos_item_name",
    "quantity_sold",
    "gross_sales",
    "discount",
    "net_sales",
    "tax",
}


def _decode_csv(uploaded_file) -> str:
    raw = uploaded_file.read()
    if isinstance(raw, str):
        return raw
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode CSV file. Please upload UTF-8 CSV.")


def _parse_date(raw_value: str):
    value = (raw_value or "").strip()
    if not value:
        raise ValueError("date is required")
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    raise ValueError("invalid date format")


def _parse_decimal(raw_value: str, field_name: str, allow_blank: bool = False) -> Decimal:
    value = (raw_value or "").strip()
    if not value and allow_blank:
        return Decimal("0")
    if not value:
        raise ValueError(f"{field_name} is required")
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field_name} must be a valid number")


def _find_mapping(pos_item_name: str) -> Optional[POSMenuItemMapping]:
    return (
        POSMenuItemMapping.objects.filter(
            is_active=True,
            pos_item_name__iexact=pos_item_name.strip(),
        )
        .select_related("recipe")
        .first()
    )


def import_pos_sales_csv(uploaded_file, user) -> Dict[str, Any]:
    decoded = _decode_csv(uploaded_file)
    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise ValueError("CSV header row is missing.")
    found_columns = {str(col).strip() for col in reader.fieldnames}
    missing = EXPECTED_COLUMNS - found_columns
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required columns: {missing_list}")

    imported_count = 0
    unmapped_count = 0
    error_count = 0
    errors: List[str] = []
    total_net_sales = Decimal("0")
    user_identifier = getattr(user, "username", None) or str(user or "System")

    for row_number, row in enumerate(reader, start=2):
        try:
            sale_day = _parse_date(row.get("date", ""))
            sale_dt = timezone.make_aware(datetime.combine(sale_day, time.min))
            pos_item_name = (row.get("pos_item_name") or "").strip()
            if not pos_item_name:
                raise ValueError("pos_item_name is required")
            quantity = _parse_decimal(row.get("quantity_sold", ""), "quantity_sold")
            if quantity <= 0:
                raise ValueError("quantity_sold must be greater than 0")
            gross_sales = _parse_decimal(row.get("gross_sales", ""), "gross_sales")
            discount = _parse_decimal(row.get("discount", ""), "discount")
            net_sales = _parse_decimal(row.get("net_sales", ""), "net_sales")
            tax = _parse_decimal(row.get("tax", ""), "tax", allow_blank=True)
            outlet = (row.get("outlet") or "").strip()
            mapping = _find_mapping(pos_item_name)
            recipe = mapping.recipe if mapping else None

            with transaction.atomic():
                SaleTransaction.objects.create(
                    recipe=recipe,
                    quantity=quantity,
                    outlet=outlet or None,
                    pos_item_name=pos_item_name,
                    gross_sales=gross_sales,
                    discount=discount,
                    net_sales=net_sales,
                    tax=tax,
                    source=SaleTransaction.Source.POS_CSV,
                    source_row_number=row_number,
                    user_id=user_identifier,
                    notes="Imported from POS CSV",
                    sale_date=sale_dt,
                )
            imported_count += 1
            total_net_sales += net_sales
            if recipe is None:
                unmapped_count += 1
        except ValueError as exc:
            error_count += 1
            errors.append(f"Row {row_number}: {exc}")

    return {
        "imported_count": imported_count,
        "unmapped_count": unmapped_count,
        "error_count": error_count,
        "errors": errors,
        "total_net_sales": total_net_sales,
    }


def apply_mapping_to_unmapped_sales(mapping: POSMenuItemMapping) -> int:
    if not mapping.recipe:
        return 0
    updated = SaleTransaction.objects.filter(
        source=SaleTransaction.Source.POS_CSV,
        recipe__isnull=True,
        pos_item_name__iexact=mapping.pos_item_name,
    ).update(recipe=mapping.recipe)
    return updated


def unmapped_sales_summary():
    return (
        SaleTransaction.objects.filter(
            source=SaleTransaction.Source.POS_CSV,
            recipe__isnull=True,
        )
        .exclude(pos_item_name__isnull=True)
        .exclude(pos_item_name__exact="")
        .values("pos_item_name")
        .annotate(
            row_count=Count("sale_id"),
            net_total=Coalesce(Sum("net_sales"), Decimal("0")),
        )
        .order_by("-net_total", "pos_item_name")
    )
