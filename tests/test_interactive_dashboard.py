import pytest
from django.urls import reverse
from django.utils import timezone

from core.viewmodels import DashboardContext
from inventory.models import Item, PurchaseOrder, StockTransaction, Supplier


@pytest.mark.django_db
def test_dashboard_context_with_filters(item_factory):
    item_factory(name="Foo")
    Supplier.objects.create(name="Supp", is_active=True)
    ctx = DashboardContext(
        labels=[],
        values=[],
        items=Item.objects.filter(is_active=True),
        suppliers=Supplier.objects.filter(is_active=True),
    ).as_dict()
    assert ctx["items"].count() == 1
    assert ctx["suppliers"].count() == 1


@pytest.mark.django_db
def test_ajax_dashboard_data_filters(client, item_factory):
    item = item_factory(name="Filtered")
    other = item_factory(name="Other")
    supplier = Supplier.objects.create(name="Supp", is_active=True)
    po = PurchaseOrder.objects.create(
        supplier=supplier, order_date=timezone.now().date()
    )
    StockTransaction.objects.create(
        item=item,
        quantity_change=5,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
        related_po_id=po.pk,
    )
    StockTransaction.objects.create(
        item=other,
        quantity_change=3,
        transaction_type="RECEIVING",
        transaction_date=timezone.now(),
    )

    day = timezone.now().date().isoformat()
    url = (
        reverse("ajax-dashboard-data")
        + f"?item={item.pk}&supplier={supplier.pk}&range=1&metric=quantity"
    )
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["labels"] == [day]
    assert data["values"] == [5.0]


@pytest.mark.django_db
def test_interactive_dashboard_redirects(client, django_user_model):
    user = django_user_model.objects.create_user(username="u", password="pw")
    client.force_login(user)
    resp = client.get(reverse("interactive-dashboard"))
    assert resp.status_code == 301
    assert resp["Location"] == "/"
