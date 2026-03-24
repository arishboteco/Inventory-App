# Phase D feature migration — renumbered from the incorrectly-named
# 0025_phase_d_features.py (0025 was already occupied by
# 0025_alter_stocksnapshot_options_and_more which is applied on production).
#
# This migration depends on 0028 and only contains operations NOT already
# covered by 0025–0028:
#   - Removes recipeitem unique_together (state + defensive DDL)
#   - Adds delivery_note_number to GoodsReceivedNote
#   - Adds direct item FK to GRNItem (ad-hoc GRN support)
#   - Adds selling_price + target_food_cost_pct to Recipe
#   - Adds sub_recipe FK to RecipeItem
#   - Adds from_department + to_department to StockTransaction
#   - Makes GoodsReceivedNote.purchase_order nullable (ad-hoc GRN)
#   - Makes GRNItem.po_item nullable
#   - Adds default=0 to GRNItem.quantity_ordered_on_po
#   - Makes RecipeItem.item nullable (sub-recipe support)
#   - Creates StockTake + StockTakeItem models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0028_alter_purchaseorder_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Remove RecipeItem unique_together(recipe, item) ────────────
        # Defensive: drop any unique constraint on recipe_items table; if the
        # constraint never existed in the live DB this is a no-op.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterUniqueTogether(
                    name="recipeitem",
                    unique_together=set(),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    DECLARE
                        r RECORD;
                    BEGIN
                        FOR r IN
                            SELECT conname
                            FROM pg_constraint
                            WHERE conrelid = 'recipe_items'::regclass
                              AND contype = 'u'
                        LOOP
                            EXECUTE 'ALTER TABLE recipe_items DROP CONSTRAINT '
                                    || quote_ident(r.conname);
                        END LOOP;
                    END $$;
                    """,
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
        ),

        # ── 2. GoodsReceivedNote: add delivery_note_number ────────────────
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

        # ── 3. GRNItem: add direct item FK (ad-hoc GRNs without a PO) ────
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

        # ── 4. Recipe: selling_price + target_food_cost_pct ──────────────
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

        # ── 5. RecipeItem: sub_recipe FK ──────────────────────────────────
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

        # ── 6. StockTransaction: from/to department FKs ──────────────────
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

        # ── 7. GoodsReceivedNote.purchase_order → nullable ────────────────
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

        # ── 8. GRNItem.po_item → nullable ────────────────────────────────
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

        # ── 9. GRNItem.quantity_ordered_on_po → default=0 ────────────────
        migrations.AlterField(
            model_name="grnitem",
            name="quantity_ordered_on_po",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),

        # ── 10. RecipeItem.item → nullable (required for sub-recipes) ─────
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

        # ── 11. Create StockTake model ────────────────────────────────────
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

        # ── 12. Create StockTakeItem model ────────────────────────────────
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
    ]
