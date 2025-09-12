from django.db import models


class Department(models.Model):
    """A department that can be associated with inventory items."""

    department_id = models.AutoField(primary_key=True)
    name = models.TextField(db_column="permitted_departments", unique=True)

    def __str__(self):
        return self.name or f"Department {self.department_id}"

    class Meta:
        managed = True
        db_table = "departments"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"], name="dept_name_idx"),
        ]


class ItemDepartment(models.Model):
    """Many-to-many relationship between items and departments."""

    item = models.ForeignKey("Item", on_delete=models.CASCADE, db_column="item_id")
    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, db_column="department_id"
    )

    class Meta:
        managed = True
        db_table = "item_departments"
        unique_together = ("item", "department")
        verbose_name = "Item Department"
        verbose_name_plural = "Item Departments"
        indexes = [
            models.Index(fields=["item"], name="itemdept_item_idx"),
            models.Index(fields=["department"], name="itemdept_dept_idx"),
        ]

    def __str__(self):
        return f"{self.item.name} - {self.department.name}"
