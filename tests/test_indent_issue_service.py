from decimal import Decimal

import pytest
from django.db import transaction

from inventory.models import Indent, IndentItem, StockTransaction
from inventory.services import indent_issue_service


@pytest.mark.django_db(transaction=True)
def test_issue_indent_locks_indent_inside_atomic_without_source_or_department(
    item_factory, django_user_model, monkeypatch
):
    user = django_user_model.objects.create_user(username="issuer")
    item = item_factory(name="Issue Rice", current_stock=Decimal("5.00"))
    indent = Indent.objects.create(
        mrn="MRN-ISSUE-001",
        requested_by="Chef",
        department=None,
        status="APPROVED",
    )
    indent_item = IndentItem.objects.create(
        indent=indent,
        item=item,
        requested_qty=Decimal("2.00"),
        issued_qty=Decimal("0.00"),
    )
    original_select_for_update = Indent.objects.select_for_update

    def guarded_select_for_update(*args, **kwargs):
        assert transaction.get_connection().in_atomic_block
        return original_select_for_update(*args, **kwargs)

    monkeypatch.setattr(Indent.objects, "select_for_update", guarded_select_for_update)

    result = indent_issue_service.issue_indent(
        indent.indent_id,
        [
            indent_issue_service.IssueLine(
                indent_item_id=indent_item.indent_item_id,
                issue_qty=Decimal("2.00"),
                source_location="",
            )
        ],
        user,
    )

    assert result.ok
    item.refresh_from_db()
    indent_item.refresh_from_db()
    indent.refresh_from_db()
    assert item.current_stock == Decimal("3.00")
    assert indent_item.issued_qty == Decimal("2.00")
    assert indent.status == "COMPLETED"
    assert StockTransaction.objects.filter(
        item=item,
        transaction_type="ISSUE",
        related_indent=indent,
        quantity_change=Decimal("-2.00"),
    ).exists()
