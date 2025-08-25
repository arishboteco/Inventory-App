from decimal import Decimal, InvalidOperation
from django.db import models

class CoerceFloatField(models.DecimalField):
    """DecimalField that coerces invalid values to Decimal('0')."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 10)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value in self.empty_values:
            return Decimal("0")
        try:
            return Decimal(value)
        except (TypeError, ValueError, InvalidOperation):
            return Decimal("0")

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)
