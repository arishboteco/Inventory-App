"""Seed realistic dashboard data for demo / development.

Usage:
    python manage.py seed_dashboard_data          # 30 days default
    python manage.py seed_dashboard_data --days 90
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventory.models import (
    Category,
    Indent,
    Item,
    PurchaseOrder,
    StockTransaction,
    Supplier,
    Unit,
)
from inventory.models.enums import IndentStatus, PurchaseOrderStatus
from inventory.models.recipes import Recipe, RecipeItem, SaleTransaction

UNITS = [
    ("kg", "kilogram"),
    ("ltr", "litre"),
    ("dz", "dozen"),
]

CATEGORIES = [
    "Meat",
    "Seafood",
    "Pantry",
    "Grains",
    "Vegetables",
    "Dairy",
]

ITEMS_SPEC = [
    ("Chicken Breast", "kg", "Meat", 8.50, 50),
    ("Salmon Fillet", "kg", "Seafood", 22.00, 30),
    ("Olive Oil", "ltr", "Pantry", 12.00, 20),
    ("Basmati Rice", "kg", "Grains", 3.50, 100),
    ("Tomatoes", "kg", "Vegetables", 4.00, 40),
    ("Mozzarella", "kg", "Dairy", 11.00, 25),
    ("Lamb Rack", "kg", "Meat", 28.00, 15),
    ("Tiger Prawns", "kg", "Seafood", 26.00, 20),
    ("Soy Sauce", "ltr", "Pantry", 5.50, 15),
    ("Flour", "kg", "Grains", 2.00, 80),
    ("Spinach", "kg", "Vegetables", 6.00, 30),
    ("Butter", "kg", "Dairy", 9.00, 20),
    ("Beef Tenderloin", "kg", "Meat", 35.00, 10),
    ("Eggs", "dz", "Dairy", 4.50, 60),
    ("Coconut Milk", "ltr", "Pantry", 3.00, 25),
]

RECIPES_SPEC = [
    {
        "name": "Grilled Chicken",
        "selling_price": 18.00,
        "target_fc": 30,
        "ingredients": [
            ("Chicken Breast", 0.25),
            ("Olive Oil", 0.02),
            ("Spinach", 0.05),
        ],
    },
    {
        "name": "Salmon Bowl",
        "selling_price": 24.00,
        "target_fc": 32,
        "ingredients": [
            ("Salmon Fillet", 0.18),
            ("Basmati Rice", 0.10),
            ("Soy Sauce", 0.01),
        ],
    },
    {
        "name": "Prawn Pasta",
        "selling_price": 22.00,
        "target_fc": 28,
        "ingredients": [("Tiger Prawns", 0.15), ("Flour", 0.08), ("Olive Oil", 0.02)],
    },
    {
        "name": "Lamb Chops",
        "selling_price": 32.00,
        "target_fc": 35,
        "ingredients": [("Lamb Rack", 0.30), ("Butter", 0.02), ("Tomatoes", 0.05)],
    },
    {
        "name": "Beef Steak",
        "selling_price": 38.00,
        "target_fc": 33,
        "ingredients": [("Beef Tenderloin", 0.25), ("Butter", 0.03), ("Spinach", 0.04)],
    },
]


class Command(BaseCommand):
    help = "Seed demo data for the redesigned dashboard"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=30, help="Number of days of transaction history"
        )

    def handle(self, *args, **options):
        days = options["days"]
        now = timezone.now()

        # Units
        unit_map = {}
        for abbr, name in UNITS:
            unit_map[abbr], _ = Unit.objects.get_or_create(
                base_unit=abbr, defaults={"unit_name": name}
            )

        # Categories
        cat_map = {}
        for cat_name in CATEGORIES:
            cat_map[cat_name], _ = Category.objects.get_or_create(category=cat_name)

        # Supplier
        supplier, _ = Supplier.objects.get_or_create(
            name="Metro Fresh Supplies", defaults={"is_active": True}
        )

        # Items
        item_map = {}
        for name, unit_abbr, cat_name, price, stock in ITEMS_SPEC:
            item, _ = Item.objects.get_or_create(
                name=name,
                defaults={
                    "unit": unit_map[unit_abbr],
                    "category": cat_map[cat_name],
                    "last_purchase_price": Decimal(str(price)),
                    "initial_purchase_price": Decimal(str(price)),
                    "current_stock": Decimal(str(stock)),
                    "reorder_point": Decimal(str(int(stock * 0.3))),
                    "is_active": True,
                },
            )
            item_map[name] = item

        # Recipes
        recipe_map = {}
        for spec in RECIPES_SPEC:
            recipe, created = Recipe.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "selling_price": Decimal(str(spec["selling_price"])),
                    "target_food_cost_pct": Decimal(str(spec["target_fc"])),
                    "is_active": True,
                    "type": "FINAL",
                },
            )
            recipe_map[spec["name"]] = recipe
            if created:
                for ing_name, qty in spec["ingredients"]:
                    item = item_map.get(ing_name)
                    if item:
                        RecipeItem.objects.create(
                            recipe=recipe,
                            item=item,
                            quantity=Decimal(str(qty)),
                            unit=item.unit.base_unit if item.unit else "kg",
                        )

        # Daily transactions
        recipes_list = list(recipe_map.values())
        items_list = list(item_map.values())
        for day_offset in range(days, 0, -1):
            day = now - timedelta(days=day_offset)

            # RECEIVING (1-3 items per day)
            for _ in range(random.randint(1, 3)):
                item = random.choice(items_list)
                qty = Decimal(str(random.randint(5, 30)))
                StockTransaction.objects.create(
                    item=item,
                    quantity_change=qty,
                    transaction_type="RECEIVING",
                    transaction_date=day,
                    notes="Seed: receiving",
                )

            # SALE transactions via SaleTransaction (2-6 per day)
            for _ in range(random.randint(2, 6)):
                recipe = random.choice(recipes_list)
                qty = Decimal(str(random.randint(1, 5)))
                SaleTransaction.objects.create(
                    recipe=recipe,
                    quantity=qty,
                    sale_date=day,
                    notes="Seed: sale",
                )

            # ISSUE transactions (1-3 per day)
            for _ in range(random.randint(1, 3)):
                item = random.choice(items_list)
                qty = Decimal(str(random.randint(1, 8)))
                StockTransaction.objects.create(
                    item=item,
                    quantity_change=-qty,
                    transaction_type="ISSUE",
                    transaction_date=day,
                    notes="Seed: issue",
                )

            # WASTAGE (0-2 per day)
            for _ in range(random.randint(0, 2)):
                item = random.choice(items_list)
                qty = Decimal(str(round(random.uniform(0.5, 3.0), 2)))
                StockTransaction.objects.create(
                    item=item,
                    quantity_change=-qty,
                    transaction_type="WASTAGE",
                    transaction_date=day,
                    notes="Seed: wastage",
                )

        # Indents (3 submitted)
        for i in range(3):
            Indent.objects.get_or_create(
                mrn=f"SEED-IND-{i+1:03d}",
                defaults={
                    "status": IndentStatus.SUBMITTED,
                    "notes": "Seeded indent",
                },
            )

        # POs (1 draft + 1 sent)
        PurchaseOrder.objects.get_or_create(
            po_number="SEED-PO-DRAFT",
            defaults={
                "supplier": supplier,
                "status": PurchaseOrderStatus.DRAFT,
            },
        )
        PurchaseOrder.objects.get_or_create(
            po_number="SEED-PO-SENT",
            defaults={
                "supplier": supplier,
                "status": PurchaseOrderStatus.SENT,
            },
        )

        # Set 4 items to low stock
        low_stock_names = [
            "Salmon Fillet",
            "Tiger Prawns",
            "Beef Tenderloin",
            "Lamb Rack",
        ]
        for name in low_stock_names:
            item = item_map.get(name)
            if item:
                item.current_stock = Decimal(
                    str(max(1, int(float(item.reorder_point or 5)) - 2))
                )
                item.save(update_fields=["current_stock"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {days} days of dashboard data with "
                f"{len(item_map)} items, {len(recipe_map)} recipes."
            )
        )
