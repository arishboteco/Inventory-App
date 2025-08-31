"""SubCategory model for hierarchical category structure."""

from django.db import models

from .category import Category


class SubCategory(models.Model):
    """Represents a sub-category belonging to a Category."""

    name = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="subcategories"
    )

    class Meta:
        db_table = "sub_categories"
        verbose_name = "Sub-category"
        verbose_name_plural = "Sub-categories"
        ordering = ["category__category", "name"]

    def __str__(self) -> str:  # pragma: no cover - simple representation
        return f"{self.category.category} > {self.name}"
