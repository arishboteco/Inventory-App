from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone

from inventory.models import Item, StockTransaction
from inventory.services import ml


def create_item(name: str) -> Item:
    return Item.objects.create(name=name, unit_id=19)


def test_forecast_returns_expected_values(db):
    item = create_item("item1")
    now = timezone.now()
    for i in range(3):
        tx = StockTransaction.objects.create(item=item, quantity_change=10)
        tx.transaction_date = now - timedelta(days=3 - i)
        tx.save(update_fields=["transaction_date"])
    forecast = ml.forecast_item_demand(item, periods=2)
    assert len(forecast) == 2
    assert forecast == pytest.approx([10, 10], rel=0.1)


def test_forecast_fallback_on_error(db, monkeypatch, caplog):
    item = create_item("item1")
    now = timezone.now()
    for i in range(2):
        tx = StockTransaction.objects.create(item=item, quantity_change=10)
        tx.transaction_date = now - timedelta(days=2 - i)
        tx.save(update_fields=["transaction_date"])

    def bad_fit(self, *args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(ml.SimpleExpSmoothing, "fit", bad_fit)
    with caplog.at_level("ERROR"):
        forecast = ml.forecast_item_demand(item, periods=3)

    assert forecast == [0.0, 0.0, 0.0]
    assert "Failed to forecast demand" in caplog.text


def test_abc_classification(db):
    item_a = create_item("A")
    item_b = create_item("B")
    item_c = create_item("C")
    for _ in range(10):
        StockTransaction.objects.create(item=item_a, quantity_change=10)
    for _ in range(3):
        StockTransaction.objects.create(item=item_b, quantity_change=10)
    StockTransaction.objects.create(item=item_c, quantity_change=10)
    classes = ml.abc_classification()
    assert classes[item_a.pk] == "A"
    assert classes[item_b.pk] == "B"
    assert classes[item_c.pk] == "C"


@pytest.mark.django_db
def test_ml_dashboard_uses_cache(client):
    # Ensure user is logged in explicitly
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user, _ = User.objects.get_or_create(username="admin")
    if not user.has_usable_password():
        user.set_password("admin")
        user.save()
    client.force_login(user)

    # Clear all caches explicitly
    cache.clear()
    from django.core.cache import caches

    for cache_name in caches:
        caches[cache_name].clear()

    with (
        patch("inventory.services.ml.queue_train_models") as mock_queue,
        patch("inventory.services.ml.abc_classification", return_value={}) as mock_abc,
    ):
        # When queue_train_models is called we synchronously populate the cache to
        # emulate the background worker completing its task.
        mock_queue.side_effect = (
            lambda periods=1, cache_key="ml_train_models", ttl=300: cache.set(
                cache_key, {}, ttl
            )
        )

        response = client.get(reverse("ml_dashboard"))
        assert response.status_code == 200
        assert mock_queue.call_count == 1
        assert mock_abc.call_count == 1

        client.get(reverse("ml_dashboard"))
        assert mock_queue.call_count == 1
        assert mock_abc.call_count == 1

        cache.clear()
        client.get(reverse("ml_dashboard"))
        assert mock_queue.call_count == 2
        assert mock_abc.call_count == 2


def test_queue_train_models_updates_cache(db):
    cache_key = "test_ml_train_models"
    cache.delete(cache_key)
    ml.queue_train_models(periods=1, cache_key=cache_key, ttl=300, sync=True)
    assert cache.get(cache_key) is not None


def test_queue_train_models_logs_exception(db, monkeypatch, caplog):
    def bad_train(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(ml, "train_models", bad_train)
    cache_key = "test_ml_train_models_error"
    cache.delete(cache_key)
    with caplog.at_level("ERROR"):
        ml.queue_train_models(periods=1, cache_key=cache_key, ttl=300, sync=True)
    assert cache.get(cache_key) is None
    assert "Failed to train forecasting models" in caplog.text
