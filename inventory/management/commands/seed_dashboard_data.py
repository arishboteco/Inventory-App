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
    ChefBulletin,
    GoodsReceivedNote,
    GRNItem,
    Indent,
    Item,
    POSMenuItemMapping,
    PurchaseOrder,
    PurchaseOrderItem,
    RecoveryAction,
    SavingsLedger,
    StockTransaction,
    Supplier,
    Unit,
    VendorItemPrice,
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
            token = abbr.upper()
            unit_map[abbr], _ = Unit.objects.get_or_create(
                base_unit=token,
                defaults={
                    "purchase_unit": token,
                    "conversion_factor": Decimal("1"),
                },
            )

        # Categories
        cat_map = {}
        for cat_name in CATEGORIES:
            cat_map[cat_name], _ = Category.objects.get_or_create(category=cat_name)

        # Supplier
        supplier, _ = Supplier.objects.get_or_create(
            name="Metro Fresh Supplies", defaults={"is_active": True}
        )
        alt_supplier, _ = Supplier.objects.get_or_create(
            name="Harborline Foods", defaults={"is_active": True}
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

            POSMenuItemMapping.objects.get_or_create(
                pos_item_name=spec["name"],
                defaults={
                    "recipe": recipe,
                    "is_active": True,
                    "notes": "Seed POS mapping",
                },
            )

        # Vendor price history for comparison pages
        for idx, item in enumerate(item_map.values()):
            base_price = Decimal(str(item.last_purchase_price or 0))
            if base_price <= 0:
                continue
            metro_price = (base_price * Decimal("1.00")).quantize(Decimal("0.01"))
            harbor_price = (base_price * (Decimal("0.94") if idx % 2 else Decimal("1.06"))).quantize(
                Decimal("0.01")
            )
            VendorItemPrice.objects.get_or_create(
                vendor=supplier,
                item=item,
                unit=item.unit,
                effective_from=now.date() - timedelta(days=10),
                defaults={"price": metro_price, "source": "Seed: metro", "is_active": True},
            )
            VendorItemPrice.objects.get_or_create(
                vendor=alt_supplier,
                item=item,
                unit=item.unit,
                effective_from=now.date() - timedelta(days=10),
                defaults={"price": harbor_price, "source": "Seed: harbor", "is_active": True},
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
                gross = (Decimal(str(recipe.selling_price or 0)) * qty).quantize(
                    Decimal("0.01")
                )
                discount = (gross * Decimal("0.04")).quantize(Decimal("0.01"))
                net = (gross - discount).quantize(Decimal("0.01"))
                tax = (net * Decimal("0.05")).quantize(Decimal("0.01"))
                SaleTransaction.objects.create(
                    recipe=recipe,
                    quantity=qty,
                    outlet="Main Outlet",
                    pos_item_name=recipe.name,
                    gross_sales=gross,
                    discount=discount,
                    net_sales=net,
                    tax=tax,
                    source=SaleTransaction.Source.POS_CSV,
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
                "order_date": now.date(),
                "status": PurchaseOrderStatus.DRAFT,
            },
        )
        po_sent, _ = PurchaseOrder.objects.get_or_create(
            po_number="SEED-PO-SENT",
            defaults={
                "supplier": supplier,
                "order_date": now.date() - timedelta(days=2),
                "status": PurchaseOrderStatus.SENT,
            },
        )

        sample_items = list(item_map.values())[:3]
        for line_idx, item in enumerate(sample_items):
            po_item, _ = PurchaseOrderItem.objects.get_or_create(
                purchase_order=po_sent,
                item=item,
                defaults={
                    "quantity_ordered": Decimal("10.00") + Decimal(line_idx),
                    "unit_price": Decimal(str(item.last_purchase_price or 0)),
                },
            )
            po_item.line_total = po_item.quantity_ordered * po_item.unit_price
            po_item.save(update_fields=["line_total"])

        grn, _ = GoodsReceivedNote.objects.get_or_create(
            grn_number="SEED-GRN-0001",
            defaults={
                "purchase_order": po_sent,
                "supplier": supplier,
                "received_date": now.date() - timedelta(days=1),
                "delivery_note_number": "SEED-DN-1001",
                "notes": "Seed GRN",
            },
        )
        for po_item in po_sent.purchaseorderitem_set.select_related("item").all():
            GRNItem.objects.get_or_create(
                grn=grn,
                po_item=po_item,
                defaults={
                    "quantity_ordered_on_po": po_item.quantity_ordered,
                    "quantity_received": po_item.quantity_ordered - Decimal("1.00"),
                    "unit_price_at_receipt": po_item.unit_price,
                    "item_notes": "Seed receipt",
                },
            )

        # Savings ledger entries (estimated / confirmed / lost / verified)
        ledger_rows = [
            {
                "date": now.date() - timedelta(days=4),
                "item": sample_items[0] if sample_items else None,
                "saving_type": SavingsLedger.SavingType.VENDOR_SAVING,
                "source_document_type": "PO",
                "source_document_id": po_sent.po_number,
                "baseline_price": Decimal("250.00"),
                "selected_price": Decimal("235.00"),
                "invoice_price": Decimal("235.00"),
                "quantity": Decimal("12.000"),
                "estimated_saving": Decimal("180.00"),
                "confirmed_saving": Decimal("180.00"),
                "lost_saving": Decimal("0.00"),
                "status": SavingsLedger.Status.CONFIRMED,
                "notes": "Seed vendor saving",
            },
            {
                "date": now.date() - timedelta(days=3),
                "item": sample_items[1] if len(sample_items) > 1 else None,
                "saving_type": SavingsLedger.SavingType.VARIANCE_REDUCTION,
                "source_document_type": "Variance",
                "source_document_id": "VR-SEED-01",
                "baseline_price": Decimal("0.00"),
                "selected_price": Decimal("0.00"),
                "invoice_price": Decimal("0.00"),
                "quantity": Decimal("0.000"),
                "estimated_saving": Decimal("120.00"),
                "confirmed_saving": Decimal("0.00"),
                "lost_saving": Decimal("0.00"),
                "status": SavingsLedger.Status.ESTIMATED,
                "notes": "Seed variance opportunity",
            },
            {
                "date": now.date() - timedelta(days=2),
                "item": sample_items[2] if len(sample_items) > 2 else None,
                "saving_type": SavingsLedger.SavingType.INVOICE_MISMATCH_CAUGHT,
                "source_document_type": "GRN",
                "source_document_id": grn.grn_number,
                "baseline_price": Decimal("140.00"),
                "selected_price": Decimal("136.00"),
                "invoice_price": Decimal("144.00"),
                "quantity": Decimal("8.000"),
                "estimated_saving": Decimal("32.00"),
                "confirmed_saving": Decimal("0.00"),
                "lost_saving": Decimal("64.00"),
                "status": SavingsLedger.Status.LOST,
                "notes": "Seed lost saving",
            },
            {
                "date": now.date() - timedelta(days=1),
                "item": sample_items[0] if sample_items else None,
                "saving_type": SavingsLedger.SavingType.WASTE_REDUCTION,
                "source_document_type": "Action",
                "source_document_id": "ACT-SEED-01",
                "baseline_price": Decimal("0.00"),
                "selected_price": Decimal("0.00"),
                "invoice_price": Decimal("0.00"),
                "quantity": Decimal("0.000"),
                "estimated_saving": Decimal("95.00"),
                "confirmed_saving": Decimal("95.00"),
                "lost_saving": Decimal("0.00"),
                "status": SavingsLedger.Status.VERIFIED,
                "notes": "Seed verified recovery",
            },
        ]
        created_ledger = []
        for row in ledger_rows:
            entry, _ = SavingsLedger.objects.get_or_create(
                date=row["date"],
                source_document_type=row["source_document_type"],
                source_document_id=row["source_document_id"],
                saving_type=row["saving_type"],
                defaults=row,
            )
            created_ledger.append(entry)

        # Phase 8/9 demo records
        first_recipe = recipes_list[0] if recipes_list else None
        bulletin = None
        if first_recipe:
            bulletin, _ = ChefBulletin.objects.get_or_create(
                recipe=first_recipe,
                period_start=now.date() - timedelta(days=7),
                period_end=now.date(),
                alert_type=ChefBulletin.AlertType.FOOD_COST_ABOVE_TARGET,
                defaults={
                    "headline": f"{first_recipe.name} cost above target",
                    "current_food_cost_pct": Decimal("37.50"),
                    "target_food_cost_pct": Decimal("30.00"),
                    "monthly_sales": Decimal("78000.00"),
                    "unrealised_profit": Decimal("5850.00"),
                    "main_cost_drivers": ["Chicken Breast", "Olive Oil"],
                    "suggested_change": "Reduce plate portion by 5% and tighten prep controls.",
                    "expected_saving": Decimal("1200.00"),
                    "risk_level": ChefBulletin.RiskLevel.MEDIUM,
                    "is_open": True,
                },
            )

        action_verified, _ = RecoveryAction.objects.get_or_create(
            title="Reduce prep wastage in grill station",
            leakage_type=RecoveryAction.LeakageType.WASTE_REDUCTION,
            defaults={
                "expected_saving": Decimal("1200.00"),
                "status": RecoveryAction.Status.VERIFIED,
                "implemented_date": now.date() - timedelta(days=1),
                "verified_saving": Decimal("950.00"),
                "linked_item": sample_items[0] if sample_items else None,
                "linked_chef_bulletin": bulletin,
                "notes": "Seed verified recovery action",
            },
        )
        action_open, _ = RecoveryAction.objects.get_or_create(
            title="Switch vendor for salmon procurement",
            leakage_type=RecoveryAction.LeakageType.VENDOR_PRICE,
            defaults={
                "expected_saving": Decimal("2200.00"),
                "status": RecoveryAction.Status.ASSIGNED,
                "due_date": now.date() + timedelta(days=5),
                "linked_item": item_map.get("Salmon Fillet"),
                "notes": "Seed open opportunity",
            },
        )
        if created_ledger:
            action_verified.linked_savings_entries.add(created_ledger[-1])
            action_open.linked_savings_entries.add(created_ledger[0])

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
                f"{len(item_map)} items, {len(recipe_map)} recipes, "
                f"{SavingsLedger.objects.count()} savings entries, and "
                f"{RecoveryAction.objects.count()} recovery actions."
            )
        )
