"""Category model mapping to existing category table."""

from django.db import models


class Category(models.Model):
    """Represents an item category and subcategory."""

    category_id = models.AutoField(primary_key=True)
    category = models.TextField()
    sub_category = models.TextField()

    class Meta:
        managed = False
        db_table = "category"

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.category} > {self.sub_category}"
