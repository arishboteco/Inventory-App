import pytest
from bs4 import BeautifulSoup
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


def test_supplier_form_marks_required_fields_and_keeps_contact_inputs_empty():
    form = SupplierForm()
    content = render_to_string(
        "inventory/_supplier_form_partial.html",
        {"form": form, "is_edit": False},
    )
    soup = BeautifulSoup(content, "html.parser")

    assert "Name*" in soup.get_text("", strip=True)
    assert "Contact person*" in soup.get_text("", strip=True)

    phone = soup.find("input", {"name": "phone"})
    email = soup.find("input", {"name": "email"})
    assert phone is not None
    assert email is not None
    assert not phone.get("placeholder")
    assert not email.get("placeholder")
    assert not phone.get("value")
    assert not email.get("value")


def test_supplier_form_footer_stays_visible_while_form_scrolls():
    form = SupplierForm()
    content = render_to_string(
        "inventory/_supplier_form_partial.html",
        {"form": form, "is_edit": False},
    )
    soup = BeautifulSoup(content, "html.parser")

    scroll_area = soup.select_one("[data-supplier-form-scroll]")
    footer = soup.select_one("[data-supplier-form-footer]")
    assert scroll_area is not None
    assert "overflow-y-auto" in scroll_area.get("class", [])
    assert footer is not None
    assert "sticky" in footer.get("class", [])


@pytest.mark.django_db
def test_supplier_table_action_icons_have_descriptive_labels(client):
    Supplier.objects.create(name="Lima Produce")

    response = client.get(reverse("suppliers_table"))

    assert response.status_code == 200
    content = response.content.decode()
    for label in [
        "Deactivate supplier Lima Produce",
        "View supplier Lima Produce",
        "Edit supplier Lima Produce",
        "Delete supplier Lima Produce",
    ]:
        assert f'title="{label}"' in content
        assert f'aria-label="{label}"' in content


@pytest.mark.django_db
def test_supplier_edit_view_returns_json(client):
    supplier = Supplier.objects.create(name="Old", contact_person="Original Contact")
    url = reverse("supplier_edit", args=[supplier.pk])
    resp = client.post(
        url,
        {"name": "New", "contact_person": "Updated Contact", "is_active": True},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
