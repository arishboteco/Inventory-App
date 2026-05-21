from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth.models import Group
from django.urls import reverse

from inventory.models import RecoveryAction

pytestmark = pytest.mark.django_db


def test_recovery_actions_list_page_lists_and_creates(client, django_user_model):
    user = django_user_model.objects.create_user(username="owner_action", password="pw")
    client.force_login(user)
    RecoveryAction.objects.create(
        title="Existing action",
        leakage_type=RecoveryAction.LeakageType.FOOD_COST_GAP,
        expected_saving=Decimal("150.00"),
    )

    response = client.get(reverse("recovery_actions_list"))

    assert response.status_code == 200
    assert b"Recovery Actions" in response.content
    assert b"Existing action" in response.content

    post_response = client.post(
        reverse("recovery_actions_list"),
        {
            "title": "New action",
            "leakage_type": RecoveryAction.LeakageType.WASTE_REDUCTION,
            "expected_saving": "200.00",
            "due_date": date.today().isoformat(),
            "notes": "Created in test",
        },
    )

    assert post_response.status_code == 302
    assert RecoveryAction.objects.filter(title="New action").exists()


def test_recovery_action_detail_status_update_verifies_and_links_ledger(
    client, django_user_model
):
    user = django_user_model.objects.create_user(username="manager_action", password="pw")
    client.force_login(user)
    action = RecoveryAction.objects.create(
        title="Verify this action",
        leakage_type=RecoveryAction.LeakageType.VENDOR_PRICE,
        expected_saving=Decimal("500.00"),
        status=RecoveryAction.Status.ASSIGNED,
    )

    detail = client.get(reverse("recovery_action_detail", kwargs={"action_id": action.pk}))
    assert detail.status_code == 200
    assert b"Verify this action" in detail.content

    status_response = client.post(
        reverse("recovery_action_status", kwargs={"action_id": action.pk}),
        {
            "status": RecoveryAction.Status.VERIFIED,
            "verified_saving": "420.00",
            "implemented_date": date.today().isoformat(),
            "notes": "Verified by manager",
        },
    )

    assert status_response.status_code == 302
    action.refresh_from_db()
    assert action.status == RecoveryAction.Status.VERIFIED
    assert action.verified_saving == Decimal("420.00")
    assert action.linked_savings_entries.count() == 1


def test_recovery_actions_list_is_role_scoped_for_purchase(client, django_user_model):
    purchase_group, _ = Group.objects.get_or_create(name="Purchase")
    user = django_user_model.objects.create_user(username="purchase_u", password="pw")
    user.groups.add(purchase_group)
    client.force_login(user)

    RecoveryAction.objects.create(
        title="Vendor saving action",
        leakage_type=RecoveryAction.LeakageType.VENDOR_PRICE,
        expected_saving=Decimal("120.00"),
    )
    RecoveryAction.objects.create(
        title="Recipe action",
        leakage_type=RecoveryAction.LeakageType.RECIPE_OPTIMISATION,
        expected_saving=Decimal("140.00"),
    )

    response = client.get(reverse("recovery_actions_list"))

    assert response.status_code == 200
    html = response.content.decode()
    assert "Vendor saving action" in html
    assert "Recipe action" not in html
