"""Daily stock snapshot service.

Takes a point-in-time record of each active item's current stock level so that
trend charts and ML forecasts have historical data to work with.
"""
from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger(__name__)


def take_daily_stock_snapshot() -> int:
    """Upsert a StockSnapshot for every active item using today's current_stock.

    Returns the number of snapshots created or updated.
    Safe to call multiple times on the same day (idempotent via update_or_create).
    """
    from ..models.items import Item, StockSnapshot

    today = timezone.now().date()
    items = list(
        Item.objects.filter(is_active=True).values(
            "item_id", "current_stock", "last_purchase_price"
        )
    )
    count = 0
    for item_data in items:
        quantity = item_data["current_stock"] or 0
        price = item_data["last_purchase_price"] or 0
        try:
            value = float(quantity) * float(price) if price else None
        except (TypeError, ValueError):
            value = None

        StockSnapshot.objects.update_or_create(
            item_id=item_data["item_id"],
            snapshot_date=today,
            defaults={"quantity": quantity, "value": value},
        )
        count += 1

    logger.info("StockSnapshot: upserted %d snapshots for %s", count, today)
    return count


def should_take_snapshot_today() -> bool:
    """Return True if no snapshot exists yet for today (used by lazy middleware)."""
    from ..models.items import StockSnapshot

    today = timezone.now().date()
    return not StockSnapshot.objects.filter(snapshot_date=today).exists()
