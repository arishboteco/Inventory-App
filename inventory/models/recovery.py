from django.db import models


class SavingsLedger(models.Model):
    class SavingType(models.TextChoices):
        VENDOR_SAVING = "VENDOR_SAVING", "Vendor saving"
        INVOICE_MISMATCH_CAUGHT = "INVOICE_MISMATCH_CAUGHT", "Invoice mismatch caught"
        RECIPE_OPTIMISATION = "RECIPE_OPTIMISATION", "Recipe optimisation"
        WASTE_REDUCTION = "WASTE_REDUCTION", "Waste reduction"
        VARIANCE_REDUCTION = "VARIANCE_REDUCTION", "Variance reduction"
        MENU_PRICE_CORRECTION = "MENU_PRICE_CORRECTION", "Menu price correction"

    class Status(models.TextChoices):
        ESTIMATED = "ESTIMATED", "Estimated"
        CONFIRMED = "CONFIRMED", "Confirmed"
        LOST = "LOST", "Lost"
        REJECTED = "REJECTED", "Rejected"
        VERIFIED = "VERIFIED", "Verified"

    date = models.DateField(db_index=True)
    outlet = models.CharField(max_length=120, blank=True, null=True)
    item = models.ForeignKey(
        "inventory.Item", on_delete=models.SET_NULL, blank=True, null=True
    )
    saving_type = models.CharField(max_length=40, choices=SavingType.choices)
    source_document_type = models.CharField(max_length=50, blank=True, default="")
    source_document_id = models.CharField(max_length=80, blank=True, default="")
    baseline_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selected_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invoice_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)
    estimated_saving = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    confirmed_saving = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    lost_saving = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ESTIMATED
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "savings_ledger"
        ordering = ["-date", "-id"]
        indexes = [
            models.Index(fields=["date"], name="sav_ledger_date_idx"),
            models.Index(fields=["status"], name="sav_ledger_status_idx"),
            models.Index(fields=["saving_type"], name="sav_ledger_type_idx"),
            models.Index(fields=["item", "date"], name="sav_ledger_item_date_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        item_name = self.item.name if self.item else "No item"
        return f"{self.get_saving_type_display()} - {item_name} ({self.date})"


class VendorItemPrice(models.Model):
    vendor = models.ForeignKey("inventory.Supplier", on_delete=models.CASCADE)
    item = models.ForeignKey("inventory.Item", on_delete=models.CASCADE)
    unit = models.ForeignKey(
        "inventory.Unit", on_delete=models.SET_NULL, blank=True, null=True
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    effective_from = models.DateField(db_index=True)
    source = models.CharField(max_length=60, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "vendor_item_prices"
        ordering = ["-effective_from", "-id"]
        indexes = [
            models.Index(fields=["vendor", "item"], name="vip_vendor_item_idx"),
            models.Index(fields=["item", "effective_from"], name="vip_item_eff_idx"),
            models.Index(fields=["is_active"], name="vip_active_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.vendor} - {self.item} @ {self.price}"
