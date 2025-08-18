import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=["django.contrib.contenttypes", "django.contrib.auth", "inventory"],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        USE_TZ=True,
    )
    django.setup()

from django.db import connection
from inventory.models import Item, Indent, IndentItem
from inventory.forms import IndentForm, IndentItemFormSet


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


def test_indent_form_and_formset_save():
    item = Item.objects.create(name="Sugar")
    form = IndentForm(
        {
            "requested_by": "Alice",
            "department": "Kitchen",
            "date_required": "2024-01-01",
            "notes": "Urgent",
        }
    )
    formset_data = {
        "items-TOTAL_FORMS": "1",
        "items-INITIAL_FORMS": "0",
        "items-MIN_NUM_FORMS": "0",
        "items-MAX_NUM_FORMS": "1000",
        "items-0-item": str(item.pk),
        "items-0-requested_qty": "5",
        "items-0-notes": "",
    }
    formset = IndentItemFormSet(formset_data, prefix="items")
    assert form.is_valid()
    assert formset.is_valid()
    indent = form.save()
    formset.instance = indent
    formset.save()
    indent.refresh_from_db()
    assert indent.status == "SUBMITTED"
    assert indent.indentitem_set.count() == 1
    assert indent.indentitem_set.first().item_id == item.pk
