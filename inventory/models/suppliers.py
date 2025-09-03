from django.db import models


class Supplier(models.Model):
    """Stores vendor contact and activity information."""

    supplier_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True, null=False, blank=False)
    contact_person = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    # Enhanced business fields
    tax_id = models.CharField(
        max_length=50, blank=True, null=True, help_text="Tax identification number"
    )
    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Standard payment terms (e.g., Net 30)",
    )
    credit_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Credit limit amount",
    )
    supplier_rating = models.IntegerField(
        blank=True, null=True, help_text="Supplier rating (1-5 stars)"
    )

    notes = models.TextField(blank=True, null=True, default="")
    is_active = models.BooleanField(default=True, null=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return self.name or f"Supplier {self.pk}"

    class Meta:
        managed = True
        db_table = "suppliers"
