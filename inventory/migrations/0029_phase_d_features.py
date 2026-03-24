# Phase D feature migration — renumbered from the incorrectly-named
# 0025_phase_d_features.py (0025 was already occupied by
# 0025_alter_stocksnapshot_options_and_more which is applied on production).
#
# STATE-ONLY migration: all operations have empty database_operations because
# the original 0025_phase_d_features was applied to the production database
# before it was deleted and renumbered. Every column/table already exists.
#
# Django's migration state is updated so the ORM knows about all Phase D
# fields and models without attempting any DDL that would fail.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0028_alter_purchaseorder_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Remove RecipeItem unique_together ──────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="recipeitem",
                    unique_together=set(),
                ),
            ],
            database_operations=[],  # Constraint already removed in production
        ),
        # ── 2. GoodsReceivedNote: delivery_note_number ────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="goodsreceivednote",
                    name="delivery_note_number",
                    field=models.CharField(
                        blank=True,
                        help_text="Delivery note or invoice number",
                        max_length=100,
                        null=True,
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 3. GRNItem: direct item FK ────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="grnitem",
                    name="item",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="direct_item_id",
                        help_text="Direct item reference (for ad-hoc GRNs without a PO)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="grn_items",
                        to="inventory.item",
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 4. Recipe: selling_price ──────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="recipe",
                    name="selling_price",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Menu selling price (ex. tax)",
                        max_digits=10,
                        null=True,
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 5. Recipe: target_food_cost_pct ──────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="recipe",
                    name="target_food_cost_pct",
                    field=models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        default=30.0,
                        help_text="Target food cost percentage for this item type",
                        max_digits=5,
                        null=True,
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 6. RecipeItem: sub_recipe FK ──────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="recipeitem",
                    name="sub_recipe",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="sub_recipe_id",
                        help_text="Sub-recipe used as an ingredient",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="used_in",
                        to="inventory.recipe",
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 7. StockTransaction: from_department FK ───────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="stocktransaction",
                    name="from_department",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Source department (for TRANSFER type only)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transfers_out",
                        to="inventory.department",
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 8. StockTransaction: to_department FK ─────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="stocktransaction",
                    name="to_department",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Destination department (for TRANSFER type only)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="transfers_in",
                        to="inventory.department",
                    ),
                ),
            ],
            database_operations=[],  # Column already exists in production
        ),
        # ── 9. GRN.purchase_order → nullable ──────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="goodsreceivednote",
                    name="purchase_order",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="po_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.purchaseorder",
                    ),
                ),
            ],
            database_operations=[],  # Already nullable in production
        ),
        # ── 10. GRNItem.po_item → nullable ────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="grnitem",
                    name="po_item",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="po_item_id",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="inventory.purchaseorderitem",
                    ),
                ),
            ],
            database_operations=[],  # Already nullable in production
        ),
        # ── 11. GRNItem.quantity_ordered_on_po → default=0 ───────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="grnitem",
                    name="quantity_ordered_on_po",
                    field=models.DecimalField(
                        decimal_places=2, default=0, max_digits=10
                    ),
                ),
            ],
            database_operations=[],  # Default already set in production
        ),
        # ── 12. RecipeItem.item → nullable ────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="recipeitem",
                    name="item",
                    field=models.ForeignKey(
                        blank=True,
                        db_column="item_id",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recipe_usages",
                        to="inventory.item",
                    ),
                ),
            ],
            database_operations=[],  # Already nullable in production
        ),
        # ── 13. StockTake model ───────────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="StockTake",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("date", models.DateField()),
                        (
                            "status",
                            models.CharField(
                                choices=[
                                    ("DRAFT", "Draft"),
                                    ("IN_PROGRESS", "In Progress"),
                                    ("COMPLETED", "Completed"),
                                ],
                                default="DRAFT",
                                max_length=20,
                            ),
                        ),
                        ("notes", models.TextField(blank=True)),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("completed_at", models.DateTimeField(blank=True, null=True)),
                        (
                            "created_by",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                        (
                            "department",
                            models.ForeignKey(
                                blank=True,
                                help_text="Leave blank for a full stock-take across all departments",
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                to="inventory.department",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "stock_takes",
                        "ordering": ["-date", "-created_at"],
                        "managed": True,
                    },
                ),
            ],
            database_operations=[],  # Table already exists in production
        ),
        # ── 14. StockTakeItem model ───────────────────────────────────────
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="StockTakeItem",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "system_qty",
                            models.DecimalField(
                                decimal_places=3,
                                help_text="Auto-populated from current stock at time of stock-take creation",
                                max_digits=10,
                            ),
                        ),
                        (
                            "physical_qty",
                            models.DecimalField(
                                blank=True,
                                decimal_places=3,
                                help_text="Actual counted quantity entered by staff",
                                max_digits=10,
                                null=True,
                            ),
                        ),
                        ("notes", models.TextField(blank=True)),
                        (
                            "item",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                to="inventory.item",
                            ),
                        ),
                        (
                            "stock_take",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="items",
                                to="inventory.stocktake",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "stock_take_items",
                        "ordering": ["item__name"],
                        "managed": True,
                    },
                ),
            ],
            database_operations=[],  # Table already exists in production
        ),
    ]
