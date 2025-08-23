import pytest
from django.test import RequestFactory
from django.http import HttpResponse, Http404
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import connection, DatabaseError, transaction
from unittest.mock import patch

from inventory.models import Item, Indent, IndentItem
from inventory.views.items import ItemEditView
from inventory.views.indents import IndentCreateView


class SimpleUser:
    is_authenticated = True


def _add_messages(request):
    # Add session and messages to the request for testing
    request.session = {}
    storage = FallbackStorage(request)
    setattr(request, "_messages", storage)
    request.user = SimpleUser()


    """
    Test that ItemEditView handles a DatabaseError during ItemForm.save gracefully.
    """
@pytest.mark.django_db
def test_item_edit_handles_save_error(item_factory):
    item = item_factory(name="Sugar")
    rf = RequestFactory()
    request = rf.post(
        f"/items/{item.pk}/edit/",
        {"name": "Sugar"},
    )
    _add_messages(request)
    # Simulate DB error on save
    with patch("inventory.forms.item_forms.get_units", return_value={}), \
        patch("inventory.forms.item_forms.get_categories", return_value={}), \
        patch("inventory.forms.item_forms.ItemForm.save", side_effect=DatabaseError), \
        patch("inventory.views.items.render", return_value=HttpResponse()):
        resp = ItemEditView.as_view()(request, pk=item.pk)
    assert resp.status_code == 200


@pytest.mark.django_db
@pytest.mark.skip(reason="This test uses raw SQL that is incompatible with PostgreSQL's strict type checking.")
def test_item_edit_handles_non_numeric_values(item_factory):
    """
    Test that ItemEditView does not crash when non-numeric values are present in numeric DB fields.
    Note: This is skipped for strict DBs like PostgreSQL, but works on SQLite.
    """
    item = item_factory(name="Flour")
    # The following will fail on PostgreSQL; works in SQLite.
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE inventory_item SET reorder_point='abc', current_stock='xyz' WHERE id=%s",
            [item.pk],
        )
    rf = RequestFactory()
    request = rf.get(f"/items/{item.pk}/edit/")
    _add_messages(request)
    with patch("inventory.forms.item_forms.get_units", return_value={}), \
        patch("inventory.views.items.render", return_value=HttpResponse()):
        resp = ItemEditView.as_view()(request, pk=item.pk)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_item_edit_db_error_returns_404():
    """
    Test that ItemEditView returns 404 if there is a database error fetching the object.
    """
    rf = RequestFactory()
    request = rf.get("/items/1/edit/")
    _add_messages(request)
    # Simulate DB error when fetching the object
    with patch("inventory.forms.item_forms.get_units", return_value={}), \
        patch("inventory.views.items.get_object_or_404", side_effect=DatabaseError):
        with pytest.raises(Http404):
            ItemEditView.as_view()(request, pk=1)


    """
    Test that IndentCreateView does not create an Indent if IndentItemFormSet.save fails.
    Ensures atomicity.
    """
@pytest.mark.django_db
def test_indent_create_atomic_on_error(item_factory):
    item = item_factory(name="Salt")
    rf = RequestFactory()
    post_data = {
        "requested_by": "Bob",
        "department": "Kitchen",
        "date_required": "2024-01-01",
        "notes": "",
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-item": str(item.pk),
        "items-0-requested_qty": "5",
        "items-0-notes": "",
    }
    request = rf.post("/indents/create/", post_data)
    _add_messages(request)
    # Simulate DB error on formset save
    with patch("inventory.forms.indent_forms.IndentItemFormSet.save", side_effect=DatabaseError):
        with patch("inventory.views.indents.render", return_value=HttpResponse()):
            resp = IndentCreateView.as_view()(request)
    assert resp.status_code == 200
    # No indent should be created on DB error
    assert Indent.objects.count() == 0
