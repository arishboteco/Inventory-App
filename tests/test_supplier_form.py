import pytest
from django.template.loader import render_to_string
from django.urls import reverse

from inventory.forms.supplier_forms import SupplierForm
from inventory.models import Supplier


@pytest.mark.django_db
def test_supplier_form_partial_renders_all_fields():
    supplier = Supplier.objects.create(name="Test Supplier")
    form = SupplierForm(instance=supplier)
    content = render_to_string(
        "inventory/_supplier_form_partial.html",
        {"form": form, "supplier": supplier, "is_edit": True},
    )
    for field in [
        "name",
        "contact_person",
        "phone",
        "email",
        "address",
        "tax_id",
        "payment_terms",
        "credit_limit",
        "supplier_rating",
        "notes",
        "is_active",
    ]:
        assert f'name="{field}"' in content


@pytest.mark.django_db
def test_supplier_edit_view_returns_json(client):
    supplier = Supplier.objects.create(name="Old")
    url = reverse("supplier_edit", args=[supplier.pk])
    resp = client.post(url, {"name": "New", "is_active": True})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
