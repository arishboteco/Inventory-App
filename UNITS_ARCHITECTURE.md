# Units Table Architecture - Correct Implementation Guide

## Overview

The application uses a sophisticated units table architecture with four key columns that enable conversion between recipe units (base) and procurement units (purchase).

## Units Table Structure

```sql
CREATE TABLE units (
    unit_id INTEGER PRIMARY KEY,         -- Unique identifier for unit relationship
    base_unit TEXT NOT NULL,            -- Unit used in recipes (cooking measurements)
    purchase_unit TEXT NOT NULL,        -- Unit used for procurement (buying measurements)
    conversion_factor REAL NOT NULL     -- Multiplier to convert purchase to base
);
```

## Architecture Logic

### 1. **unit_id** - Application Reference
- **Purpose**: Unique identifier for a specific unit conversion relationship
- **Usage**: Foreign key in items table (`item.unit_id`)
- **Example**: `unit_id=19`, `unit_id=1`, `unit_id=12`

### 2. **base_unit** - Recipe Measurements
- **Purpose**: Unit used in recipes and cooking operations
- **Usage**: Recipe calculations, kitchen operations, portion control
- **Examples**: `grams`, `litres`, `pieces`, `kilograms`
- **Context**: What chefs use when preparing food

### 3. **purchase_unit** - Procurement Measurements  
- **Purpose**: Unit used when purchasing from suppliers
- **Usage**: Purchase orders, invoicing, supplier negotiations
- **Examples**: `KG`, `BOX`, `BOTTLE`, `CASE`
- **Context**: How suppliers sell and invoice items

### 4. **conversion_factor** - Unit Conversion
- **Purpose**: Multiplier to convert from purchase_unit to base_unit
- **Usage**: Convert procurement quantities to recipe quantities
- **Formula**: `base_quantity = purchase_quantity × conversion_factor`
- **Examples**: `1000.0` (1 KG = 1000 grams), `1.0` (1 BOTTLE = 1 pieces)

## Real Database Examples

```
unit_id | base_unit | purchase_unit | conversion_factor
--------|-----------|---------------|------------------
19      | kg        | KG           | 1.0
1       | grams     | KG           | 1000.0
12      | pieces    | BOX          | 24.0
5       | litres    | CASE         | 12.0
```

## Business Logic Examples

### Example 1: Rice (unit_id=1)
- **Base Unit**: `grams` (recipes use gram measurements)
- **Purchase Unit**: `KG` (suppliers sell in kilograms)
- **Conversion**: `1000.0` (1 KG = 1000 grams)
- **Scenario**: Buy 25 KG rice → Recipe has 25,000 grams available

### Example 2: Beer Bottles (unit_id=12)
- **Base Unit**: `pieces` (recipes count individual bottles)
- **Purchase Unit**: `BOX` (suppliers sell in boxes)
- **Conversion**: `24.0` (1 BOX = 24 pieces)
- **Scenario**: Buy 10 BOX beer → Recipe has 240 pieces available

### Example 3: Olive Oil (unit_id=5)
- **Base Unit**: `litres` (recipes measure in litres)
- **Purchase Unit**: `CASE` (suppliers sell in cases)
- **Conversion**: `12.0` (1 CASE = 12 litres)
- **Scenario**: Buy 5 CASE oil → Recipe has 60 litres available

## Implementation in Code

### Item Model
```python
class Item(models.Model):
    unit_id = models.BigIntegerField()  # References units.unit_id
    # DON'T store separate unit fields - derive from units table
```

### Units Service Usage
```python
from inventory.services.units_service import UnitsService

# Get display names for UI
base_unit = UnitsService.get_base_unit_display(unit_id=19)  # "kg"
purchase_unit = UnitsService.get_purchase_unit_display(unit_id=19)  # "KG"

# Convert between units
base_qty = UnitsService.convert_purchase_to_base(25, unit_id=1)  # 25 KG → 25000 grams
purchase_qty = UnitsService.convert_base_to_purchase(25000, unit_id=1)  # 25000 grams → 25 KG

# Get unit info for processing
unit_info = UnitsService.get_unit_info(unit_id=1)
# Returns: {'unit_id': 1, 'base_unit': 'grams', 'purchase_unit': 'KG', 'conversion_factor': 1000.0}
```

## Use Cases

### Recipe Management
- **Input**: Recipe needs 500 grams rice
- **Storage**: Store as base_unit quantity in recipe
- **Calculation**: Calculate portions using base_unit measurements
- **Display**: Show "500 grams" to kitchen staff

### Purchase Orders  
- **Input**: Need to buy rice for recipes requiring 25,000 grams total
- **Conversion**: 25,000 grams ÷ 1000 = 25 KG needed
- **Order**: Create purchase order for 25 KG
- **Display**: Show "25 KG" to purchasing team

### Stock Management
- **Receiving**: Receive 25 KG rice from supplier
- **Conversion**: 25 KG × 1000 = 25,000 grams added to stock
- **Usage**: Deduct recipe quantities in grams from stock
- **Reporting**: Show both purchase and base units in reports

## Benefits

1. **Dual Unit System**: Supports both kitchen and procurement needs
2. **Automatic Conversion**: Seamless conversion between unit types
3. **Accuracy**: Precise quantity tracking across operations
4. **Flexibility**: Easy to add new unit relationships
5. **Consistency**: Single source of truth for unit definitions

## Display Guidelines

### Kitchen Views
- **Use base_unit**: Show quantities in cooking-friendly units
- **Example**: "Recipe uses 500 grams flour"
- **Context**: What kitchen staff understand and measure

### Procurement Views  
- **Use purchase_unit**: Show quantities in supplier-friendly units
- **Example**: "Order 25 KG flour from supplier"
- **Context**: What purchasing team negotiates and orders

### Conversion Views
- **Show both units**: Display conversion relationships clearly
- **Example**: "1 KG = 1000 grams" or "25 KG → 25,000 grams"
- **Context**: Help users understand unit relationships

## API Patterns

### Recommended Usage
```python
# ✅ CORRECT: Use UnitsService
from inventory.services.units_service import UnitsService

# Get unit display for UI
display = UnitsService.get_base_unit_display(item.unit_id)

# Convert quantities for calculations
recipe_qty = UnitsService.convert_purchase_to_base(purchase_qty, item.unit_id)

# Form choices
choices = UnitsService.get_unit_choices_for_forms()
```

### Legacy Patterns (Avoid)
```python
# ❌ INCORRECT: Direct unit_id display
display = str(item.unit_id)  # Shows "19" instead of "kg"

# ❌ INCORRECT: Manual conversions
converted = purchase_qty * 1000  # Hard-coded conversion factor

# ❌ INCORRECT: Direct database queries
cursor.execute("SELECT base_unit FROM units WHERE unit_id = ?", [unit_id])
```

## Testing Strategy

The test environment includes fallback unit data:
```python
fallback_units = {
    1: {'base_unit': 'grams', 'purchase_unit': 'KG', 'conversion_factor': 1000.0},
    19: {'base_unit': 'kg', 'purchase_unit': 'KG', 'conversion_factor': 1.0},
    12: {'base_unit': 'pieces', 'purchase_unit': 'BOX', 'conversion_factor': 24.0},
}
```

Tests should use valid `unit_id` values and verify proper unit display and conversion behavior.

## Common Pitfalls

### ❌ Wrong: Displaying unit_id directly
```python
# Shows "19" instead of "kg"
f"Quantity: {quantity} {item.unit_id}"
```

### ✅ Correct: Using UnitsService for display
```python
# Shows "2 kg" properly formatted
unit_display = UnitsService.get_base_unit_display(item.unit_id)
f"Quantity: {quantity} {unit_display}"
```

### ❌ Wrong: Manual conversion calculations
```python
# Hard-coded conversion - breaks when units change
base_qty = purchase_qty * 1000  # Assumes KG to grams
```

### ✅ Correct: Using UnitsService for conversions
```python
# Automatic conversion using correct factor
base_qty = UnitsService.convert_purchase_to_base(purchase_qty, item.unit_id)
```

## Current Architecture Status

### ✅ **Implemented**
- Complete UnitsService with all unit operations
- Proper unit display functions for UI
- Accurate conversion calculations between unit types
- Fallback data for test environments
- Fixed failing tests using correct unit expectations

### 📋 **Usage Guidelines**
1. Always use UnitsService for unit display and conversions
2. Store only unit_id in item records - derive display names dynamically
3. Use base_unit for recipe/kitchen operations
4. Use purchase_unit for procurement/supplier operations
5. Test with both database and fallback unit data
