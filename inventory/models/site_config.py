"""SiteConfig — singleton model for app-wide configuration."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import models

_SITECONFIG_CACHE_KEY = "site_config:row:v1"
_SITECONFIG_CACHE_TTL = 900


class SiteConfig(models.Model):
    """Singleton model storing app-wide display and business settings.

    Only one row (pk=1) should ever exist. Use ``SiteConfig.get()`` rather
    than constructing or querying directly.
    """

    business_name = models.CharField(
        max_length=100,
        default="Inventory Pro",
        help_text="Displayed in page headers and reports.",
    )
    default_food_cost_target = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30,
        help_text="Default target food cost % used in recipe costing.",
    )
    quantity_decimal_places = models.IntegerField(
        default=2,
        choices=[(0, "0"), (1, "1"), (2, "2"), (3, "3"), (4, "4")],
        help_text="Number of decimal places shown for stock quantities and conversion factors.",
    )

    class Meta:
        managed = True
        db_table = "site_config"
        verbose_name = "Site Configuration"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce singleton
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # prevent deletion

    @classmethod
    def get(cls) -> SiteConfig:
        if getattr(settings, "DISABLE_SITECONFIG_CACHE", False):
            obj, _ = cls.objects.get_or_create(pk=1)
            return obj
        raw = cache.get(_SITECONFIG_CACHE_KEY)
        if raw is not None:
            obj = cls(
                business_name=raw["business_name"],
                default_food_cost_target=Decimal(str(raw["default_food_cost_target"])),
                quantity_decimal_places=raw["quantity_decimal_places"],
            )
            obj.pk = 1
            obj._state.adding = False
            obj._state.db = "default"
            return obj
        obj, _ = cls.objects.get_or_create(pk=1)
        cache.set(
            _SITECONFIG_CACHE_KEY,
            {
                "business_name": obj.business_name,
                "default_food_cost_target": str(obj.default_food_cost_target),
                "quantity_decimal_places": obj.quantity_decimal_places,
            },
            _SITECONFIG_CACHE_TTL,
        )
        return obj

    def __str__(self) -> str:  # pragma: no cover
        return f"SiteConfig — {self.business_name}"
