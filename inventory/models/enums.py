from django.db import models


class IndentStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SUBMITTED = "SUBMITTED", "Submitted"
    PROCESSING = "PROCESSING", "Processing"
    APPROVED = "APPROVED", "Approved"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ItemStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Issue"
    ISSUED = "ISSUED", "Issued"
    CANCELLED = "CANCELLED", "Cancelled"


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ORDERED = "ORDERED", "Ordered"
    PARTIAL = "PARTIAL", "Partially Received"
    COMPLETE = "COMPLETE", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"
