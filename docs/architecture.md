# Architecture Reference

Schema documentation for the two lookup tables that underpin item classification and unit management.

---

## Category Schema

The `category` table uses three columns to enable hierarchical categorisation with unique category/sub_category combinations.

### Table Structure

```sql
CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,  -- Unique ID for this combination
    category    TEXT NOT NULL,        -- Primary grouping (Grocery, Perishable, etc.)
    sub_category TEXT NOT NULL        -- Subdivision (Dairy, Meat And Poultry, etc.)
);
```

### Example Rows

```
category_id | category    | sub_category
------------|-------------|------------------
1           | Grocery     | Juices And Purees
2           | Perishable  | Meat And Poultry
3           | Liquor      | Tequila
8           | Beer        | Bottled Beer
47          | Grocery     | Baking
```

### Usage in Code

The `Item` model stores `category_id` as a foreign key reference. Use `CategoriesService` for all display and lookup operations — never read `category`/`sub_category` text fields directly from items.

```python
from inventory.services.categories_service import CategoriesService

# Display
display = CategoriesService.get_full_category_display(category_id=8)  # "Beer > Bottled Beer"

# Lookup
category_id = CategoriesService.find_category_id('Grocery', 'Baking')  # 47

# Form choices
choices = CategoriesService.get_category_choices_for_forms()
```

---

## Units Schema

The `units` table uses four columns to enable flexible unit management and automatic conversion between purchase units and recipe base units.

### Table Structure

```sql
CREATE TABLE units (
    unit_id           INTEGER PRIMARY KEY,
    base_unit         TEXT    NOT NULL,  -- Standard unit for recipes (GM, ML, PC)
    purchase_unit     TEXT    NOT NULL,  -- Unit for procurement (2 KG, 50 GM PKT, PC)
    conversion_factor NUMERIC NOT NULL   -- Multiplier: purchase → base
);
```

### Example Rows

```
unit_id | base_unit | purchase_unit | conversion_factor
--------|-----------|---------------|------------------
1       | GM        | 2 KG          | 2000.000000
2       | GM        | 50 GM PKT     | 50.000000
19      | GM        | KG            | 1000.000000
55      | PC        | PC            | 1.000000
```

**Formula:** `base_amount = purchase_amount × conversion_factor`

### Usage in Code

The `Item` model stores `unit_id`. Use `UnitsService` for all conversions and display — do not store `base_unit`/`purchase_unit` separately on items.

```python
from inventory.services.units_service import UnitsService

# Display
label = UnitsService.get_purchase_unit_display(unit_id=1)  # "2 KG"

# Convert purchase → base for recipe calculations
grams = UnitsService.convert_purchase_to_base(quantity=1.5, unit_id=1)  # 3000 GM

# Cost calculation: purchase price ÷ conversion_factor = cost per base unit
# e.g. $10 / 2 KG bag → $10 ÷ 2000 = $0.005 per GM
```

### Test Fallback Data

Tests use these `unit_id` values:

```python
fallback_units = {
    1:  {'base_unit': 'GM', 'purchase_unit': '2 KG',  'conversion_factor': 2000.0},
    19: {'base_unit': 'GM', 'purchase_unit': 'KG',    'conversion_factor': 1000.0},
    55: {'base_unit': 'PC', 'purchase_unit': 'PC',    'conversion_factor': 1.0},
}
```

Use `unit_id=19` when expecting "KG", not `unit_id=1` which returns "2 KG".
