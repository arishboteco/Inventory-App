"""SiteConfig — singleton model for app-wide configuration."""

from __future__ import annotations

from django.db import models


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
    currency_symbol = models.CharField(
        max_length=5,
        default="$",
        help_text="Prefix used for all monetary values (e.g. $, £, €, ₹).",
    )
    default_food_cost_target = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30,
        help_text="Default target food cost % used in recipe costing.",
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
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:  # pragma: no cover
        return f"SiteConfig — {self.business_name}"
