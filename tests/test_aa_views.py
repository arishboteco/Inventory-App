import django
from django.conf import settings
from pathlib import Path
import pytest

if not settings.configured:
    BASE_DIR = Path(__file__).resolve().parent.parent
    settings.configure(
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.messages",
            "inventory",
        ],
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.middleware.common.CommonMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        ROOT_URLCONF="inventory.ui_urls",
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [BASE_DIR / "templates"],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                    ]
                },
            }
        ],
        SECRET_KEY="test",
        ALLOWED_HOSTS=["testserver"],
        USE_TZ=True,
    )
    django.setup()

from django.test import RequestFactory
from django.http import HttpResponse, Http404
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import connection, DatabaseError
from unittest.mock import patch

from inventory.models import Item, Indent, IndentItem
from inventory.views.items import ItemEditView
from inventory.views.indents import IndentCreateView


def setup_module(module):
    with connection.schema_editor() as editor:
        editor.create_model(Item)
        editor.create_model(Indent)
        editor.create_model(IndentItem)


def teardown_module(module):
    with connection.schema_editor() as editor:
        editor.delete_model(IndentItem)
        editor.delete_model(Indent)
        editor.delete_model(Item)


def _add_messages(request):
    request.session = {}
    storage = FallbackStorage(request)
    setattr(request, "_messages", storage)


def test_item_edit_handles_save_error():
    item = Item.objects.create(name="Sugar")
    rf = RequestFactory()
    request = rf.post("/items/%d/edit/" % item.pk, {"name": "Sugar"})
    _add_messages(request)
    with patch("inventory.forms.ItemForm.save", side_effect=DatabaseError):
        with patch("inventory.views.items.render", return_value=HttpResponse()):
            resp = ItemEditView.as_view()(request, pk=item.pk)
    assert resp.status_code == 200


def test_item_edit_handles_non_numeric_values():
    item = Item.objects.create(name="Flour")
    with connection.cursor() as cur:
        cur.execute(
            "UPDATE items SET reorder_point='abc', current_stock='xyz' WHERE item_id=?",
            [item.pk],
        )
    rf = RequestFactory()
    request = rf.get(f"/items/{item.pk}/edit/")
    _add_messages(request)
    with patch("inventory.views.items.render", return_value=HttpResponse()):
        resp = ItemEditView.as_view()(request, pk=item.pk)
    assert resp.status_code == 200


def test_item_edit_db_error_returns_404():
    rf = RequestFactory()
    request = rf.get("/items/1/edit/")
    with patch("inventory.views.items.get_object_or_404", side_effect=DatabaseError):
        with pytest.raises(Http404):
            ItemEditView.as_view()(request, pk=1)


def test_indent_create_atomic_on_error():
    item = Item.objects.create(name="Salt")
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
    with patch("inventory.forms.IndentItemFormSet.save", side_effect=DatabaseError):
        with patch("inventory.views.indents.render", return_value=HttpResponse()):
            resp = IndentCreateView.as_view()(request)
    assert resp.status_code == 200
    assert Indent.objects.count() == 0
