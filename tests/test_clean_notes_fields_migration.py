import importlib

from django.apps import apps as django_apps
from django.db import connection

migration_module = importlib.import_module(
    "inventory.migrations.0012_alter_goodsreceivednote_notes_and_more"
)
clean_notes_fields = migration_module.clean_notes_fields


def test_clean_notes_fields_skips_missing_tables(monkeypatch):
    class DummySchemaEditor:
        connection = connection

    # Simulate absence of all tables
    monkeypatch.setattr(
        connection.introspection, "table_names", lambda cursor=None: []
    )

    grn_model = django_apps.get_model("inventory", "GoodsReceivedNote")

    def fail_filter(*args, **kwargs):  # pragma: no cover - executed only on failure
        raise AssertionError("filter should not be called when table is missing")

    monkeypatch.setattr(grn_model.objects, "filter", fail_filter)

    clean_notes_fields(django_apps, DummySchemaEditor())

