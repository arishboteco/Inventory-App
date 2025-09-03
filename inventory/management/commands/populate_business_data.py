"""Management command to populate sample business data."""

from django.core.management.base import BaseCommand
from django.db import transaction

from inventory.models import Department, Item, Supplier
from inventory.services.form_service import clear_form_caches


class Command(BaseCommand):
    help = "Populate sample business data for testing enhanced forms"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Populating sample business data..."))

        with transaction.atomic():
            # Create sample departments if they don't exist
            departments_data = [
                {"department_id": 1, "name": "Kitchen"},
                {"department_id": 2, "name": "Storage"},
                {"department_id": 3, "name": "Front of House"},
                {"department_id": 4, "name": "Administration"},
            ]

            for dept_data in departments_data:
                dept, created = Department.objects.get_or_create(
                    department_id=dept_data["department_id"],
                    defaults={"name": dept_data["name"]},
                )
                if created:
                    self.stdout.write(f"  Created department: {dept.name}")

            # Create sample suppliers with enhanced fields
            suppliers_data = [
                {
                    "name": "Fresh Foods Supply Co.",
                    "contact_person": "John Smith",
                    "phone": "+1 (555) 123-4567",
                    "email": "orders@freshfoods.com",
                    "address": "123 Supplier St, Food City, FC 12345",
                    "tax_id": "EIN-12-3456789",
                    "payment_terms": "Net 30",
                    "credit_limit": 50000.00,
                    "supplier_rating": 5,
                    "notes": "Reliable supplier for fresh produce",
                },
                {
                    "name": "Quality Packaging Solutions",
                    "contact_person": "Sarah Johnson",
                    "phone": "+1 (555) 987-6543",
                    "email": "sales@qualitypkg.com",
                    "address": "456 Package Ave, Container City, CC 67890",
                    "tax_id": "EIN-98-7654321",
                    "payment_terms": "Net 15",
                    "credit_limit": 25000.00,
                    "supplier_rating": 4,
                    "notes": "Good pricing on bulk packaging materials",
                },
            ]

            for supplier_data in suppliers_data:
                supplier, created = Supplier.objects.get_or_create(
                    name=supplier_data["name"], defaults=supplier_data
                )
                if created:
                    self.stdout.write(f"  Created supplier: {supplier.name}")

            # Update existing items with enhanced business fields
            fresh_foods = Supplier.objects.filter(name="Fresh Foods Supply Co.").first()

            items_to_update = [
                {
                    "name": "Tomatoes",
                    "base_unit": "kg",
                    "purchase_unit": "kg",
                    "category": "Food & Beverage",
                    "sub_category": "Vegetables",
                    "initial_purchase_price": 3.50,
                    "preferred_supplier": fresh_foods,
                    "minimum_order_qty": 5.0,
                    "lead_time_days": 2,
                },
                {
                    "name": "Flour",
                    "base_unit": "kg",
                    "purchase_unit": "kg",
                    "category": "Raw Materials",
                    "sub_category": "Baking",
                    "initial_purchase_price": 2.25,
                    "preferred_supplier": fresh_foods,
                    "minimum_order_qty": 25.0,
                    "lead_time_days": 3,
                },
            ]

            updated_count = 0
            for item_data in items_to_update:
                items = Item.objects.filter(name__icontains=item_data["name"])
                for item in items:
                    for field, value in item_data.items():
                        if field != "name" and hasattr(item, field):
                            setattr(item, field, value)
                    item.save()
                    updated_count += 1
                    self.stdout.write(f"  Updated item: {item.name}")

            # Clear form caches to reload new data
            clear_form_caches()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully populated sample data:\n"
                    f"  - Departments: {len(departments_data)}\n"
                    f"  - Suppliers: {len(suppliers_data)}\n"
                    f"  - Updated items: {updated_count}"
                )
            )
