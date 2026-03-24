from decimal import Decimal

from django.db import models
from django.utils import timezone


class StockTake(models.Model):
    """D4: A physical stock-count session."""

    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("IN_PROGRESS", "In Progress"),
        ("COMPLETED", "Completed"),
    ]

    date = models.DateField()
    department = models.ForeignKey(
        "Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Leave blank for a full stock-take across all departments",
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="DRAFT"
    )
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("auth.User", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Stock Take {self.pk} — {self.date} ({self.get_status_display()})"

    class Meta:
        managed = True
        db_table = "stock_takes"
        ordering = ["-date", "-created_at"]


class StockTakeItem(models.Model):
    """D4: A single item line within a stock-take, recording system vs physical qty."""

    stock_take = models.ForeignKey(
        StockTake, related_name="items", on_delete=models.CASCADE
    )
    item = models.ForeignKey("Item", on_delete=models.CASCADE)
    system_qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Auto-populated from current stock at time of stock-take creation",
    )
    physical_qty = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Actual counted quantity entered by staff",
    )
    notes = models.TextField(blank=True)

    @property
    def variance(self):
        if self.physical_qty is not None:
            return self.physical_qty - self.system_qty
        return None

    @property
    def variance_pct(self):
        if self.variance is not None and self.system_qty > 0:
            return round(float(self.variance / self.system_qty) * 100, 1)
        return None

    @property
    def variance_status(self):
        v = self.variance
        if v is None:
            return "pending"
        if abs(v) < Decimal("0.01"):
            return "match"
        return "variance"

    def __str__(self) -> str:  # pragma: no cover
        return f"StockTakeItem {self.pk} — {self.item}"

    class Meta:
        managed = True
        db_table = "stock_take_items"
        ordering = ["item__name"]
