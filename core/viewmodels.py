"""Helper dataclasses for views."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from django.db.models import QuerySet
from django.urls import reverse

from inventory.models import Item, Supplier
from inventory.services.stock_utils import get_low_stock_items


@dataclass
class DashboardContext:
    """Assemble context data for dashboard templates.

    Parameters
    ----------
    labels:
        List of labels for trend chart.
    values:
        Corresponding values for trend chart.
    items:
        Optional queryset of active items for filter dropdown.
    suppliers:
        Optional queryset of active suppliers for filter dropdown.
    """

    labels: list[str]
    values: list[float]
    items: Optional[QuerySet[Item]] = None
    suppliers: Optional[QuerySet[Supplier]] = None

    def as_dict(self) -> dict:
        """Return the assembled context as a dictionary."""
        context = {
            "low_stock": get_low_stock_items(),
            "trend_labels": json.dumps(self.labels),
            "trend_values": json.dumps(self.values),
            "list_url": reverse("dashboard"),
            "list_title": "Dashboard",
            "current_title": "Dashboard",
        }
        if self.items is not None:
            context["items"] = self.items
        if self.suppliers is not None:
            context["suppliers"] = self.suppliers
        return context
