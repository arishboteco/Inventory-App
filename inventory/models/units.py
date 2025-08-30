from django.db import models


class Unit(models.Model):
    """Measurement unit with conversion details."""

    unit_id = models.AutoField(primary_key=True)
    base_unit = models.CharField(max_length=10)
    purchase_unit = models.CharField(max_length=50)
    conversion_factor = models.FloatField()
    is_default = models.BooleanField(default=False)

    class Meta:
        managed = True
        db_table = "units"
        ordering = ["base_unit", "purchase_unit"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.purchase_unit} ({self.base_unit})"
