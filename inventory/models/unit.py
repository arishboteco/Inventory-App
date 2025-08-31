"""Unit model mapping to existing units table."""

from django.db import models


class Unit(models.Model):
    """Measurement units used by items."""

    purchase_unit = models.TextField()
    base_unit = models.TextField()
    conversion_factor = models.DecimalField(max_digits=18, decimal_places=6)
    unit_id = models.AutoField(primary_key=True)

    class Meta:
        managed = True
        db_table = "units"
        verbose_name = "Unit"
        verbose_name_plural = "Units"
        ordering = ["base_unit", "purchase_unit"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.purchase_unit} ({self.base_unit})"
