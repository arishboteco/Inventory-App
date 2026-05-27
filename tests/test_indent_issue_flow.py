from decimal import Decimal

import pytest
from bs4 import BeautifulSoup
from django.urls import reverse

from inventory.models import Indent, IndentItem, StockTransaction
from inventory.models.enums import IndentStatus

pytestmark = pytest.mark.django_db


def _create_indent_line(item, requested=Decimal("100.00"), issued=Decimal("0.00")):
    indent = Indent.objects.create(
        mrn="MRN-ISSUE-001",
        requested_by="Kitchen",
        status=IndentStatus.APPROVED,
    )
    line = IndentItem.objects.create(
        indent=indent,
        item=item,
        requested_qty=requested,
        issued_qty=issued,
    )
    return indent, line


def test_issue_indent_page_shows_available_stock_and_location_select(
    client, item_factory
):
    item = item_factory(name="Issue Stock Item", current_stock=Decimal("20.00"))
    indent, _line = _create_indent_line(item)

    resp = client.get(reverse("issue_indent", kwargs={"pk": indent.pk}))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(), "html.parser")
    assert soup.find(string="Available") is not None
    assert (
        soup.find("td", attrs={"data-testid": "available-stock"}).get_text(strip=True)
        == "20.00"
    )
    source = soup.find("select", attrs={"name": "form-0-source_location"})
    assert source is not None
    options = [option["value"] for option in source.find_all("option")]
    assert options == [
        "",
        "Main Store",
        "Kitchen - Indiqube",
        "Kitchen - Bagmane",
        "Bar - Indiqube",
        "Bar - Bagmane",
    ]
    assert "Freezer" not in options
    issue_qty = soup.find("input", attrs={"name": "form-0-issue_qty"})
    assert issue_qty["value"] == "20.00"
    assert issue_qty["max"] == "20.00"
    assert (
        soup.find("span", attrs={"data-testid": "issue-available-help"}).get_text(
            strip=True
        )
        == "Available: 20.00"
    )
    assert (
        soup.find("td", attrs={"data-testid": "pending-qty"}).get_text(strip=True)
        == "100.00"
    )
    assert "Create PO for shortage" in resp.content.decode()


def test_issue_indent_post_issues_available_qty_and_leaves_shortage(
    client, item_factory
):
    item = item_factory(name="Short Issue Item", current_stock=Decimal("20.00"))
    indent, line = _create_indent_line(item)

    resp = client.post(
        reverse("issue_indent", kwargs={"pk": indent.pk}),
        {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-indent_item_id": str(line.pk),
            "form-0-issue_qty": "100.00",
            "form-0-source_location": "Main Store",
        },
    )

    assert resp.status_code == 302
    item.refresh_from_db()
    line.refresh_from_db()
    assert item.current_stock == Decimal("0.00")
    assert line.issued_qty == Decimal("20.00")
    assert StockTransaction.objects.filter(
        item=item,
        transaction_type="ISSUE",
        quantity_change=Decimal("-20.00"),
    ).exists()


def test_issue_indent_post_over_available_returns_detail_without_error(
    client, item_factory
):
    item = item_factory(name="Follow Short Issue Item", current_stock=Decimal("20.00"))
    indent, line = _create_indent_line(item)

    resp = client.post(
        reverse("issue_indent", kwargs={"pk": indent.pk}),
        {
            "form-TOTAL_FORMS": "1",
            "form-INITIAL_FORMS": "1",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
            "form-0-indent_item_id": str(line.pk),
            "form-0-issue_qty": "100.00",
            "form-0-source_location": "Main Store",
        },
        follow=True,
    )

    assert resp.status_code == 200
    assert "Something went wrong" not in resp.content.decode()
    assert resp.request["PATH_INFO"] == reverse(
        "indent_detail", kwargs={"pk": indent.pk}
    )


def test_processing_indent_table_has_issue_action(client, item_factory):
    item = item_factory(name="Processing List Item", current_stock=Decimal("20.00"))
    indent, _line = _create_indent_line(item)
    indent.status = IndentStatus.PROCESSING
    indent.save(update_fields=["status"])

    resp = client.get(reverse("indents_table"))

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(), "html.parser")
    issue_url = reverse("issue_indent", kwargs={"pk": indent.pk})
    issue_link = soup.find("a", href=issue_url)
    assert issue_link is not None
    assert issue_link["aria-label"] == "Issue stock"


def test_indent_drawer_has_issue_action_for_processing_indent(client, item_factory):
    item = item_factory(name="Processing Drawer Item", current_stock=Decimal("20.00"))
    indent, _line = _create_indent_line(item)
    indent.status = IndentStatus.PROCESSING
    indent.save(update_fields=["status"])

    resp = client.get(reverse("indent_detail", kwargs={"pk": indent.pk}) + "?partial=1")

    assert resp.status_code == 200
    soup = BeautifulSoup(resp.content.decode(), "html.parser")
    issue_url = reverse("issue_indent", kwargs={"pk": indent.pk})
    issue_link = soup.find("a", href=issue_url)
    assert issue_link is not None
    assert issue_link.get_text(strip=True) == "Issue Stock"
