# Units Table Architecture - Correct Implementation Guide

## Overview

The application uses a proper units table architecture with four key columns that enable flexible unit management and automatic conversions between purchase units and recipe units.

## Units Table Structure

```sql
CREATE TABLE units (
    unit_id INTEGER PRIMARY KEY,      -- Unique identifier used across application
    base_unit TEXT NOT NULL,          -- Standard unit for recipes (GM, ML, PC)
    purchase_unit TEXT NOT NULL,      -- Unit for procurement (2 KG, 50 GM PKT, PC)
    conversion_factor NUMERIC NOT NULL -- Factor to convert purchase → base
);
```

## Architecture Logic

### 1. **unit_id** - Application Reference
- **Purpose**: Unique identifier used across the application
- **Usage**: Foreign key in items table (`item.unit_id`) 
- **Example**: `unit_id=1`, `unit_id=19`, `unit_id=55`

### 2. **base_unit** - Recipe Standard
- **Purpose**: Standardized unit for recipes and calculations
- **Usage**: Recipe components, nutritional calculations, inventory math
- **Examples**: `GM` (grams), `ML` (milliliters), `PC` (pieces)
- **Benefit**: All recipes use consistent base units regardless of purchase packaging

### 3. **purchase_unit** - Procurement Unit
- **Purpose**: Unit in which items are actually purchased
- **Usage**: Display to users, purchase orders, supplier communication
- **Examples**: `2 KG` (2-kilogram bags), `50 GM PKT` (50-gram packets), `PC` (individual pieces)
- **Benefit**: Matches real-world purchasing while enabling standardized calculations

### 4. **conversion_factor** - Unit Conversion
- **Purpose**: Numeric multiplier to convert purchase_unit → base_unit
- **Usage**: Automatic conversions between display and calculation units
- **Formula**: `base_amount = purchase_amount × conversion_factor`

## Real Database Examples

```
unit_id | base_unit | purchase_unit | conversion_factor
--------|-----------|---------------|------------------
1       | GM        | 2 KG          | 2000.000000
2       | GM        | 50 GM PKT     | 50.000000  
19      | GM        | KG            | 1000.000000
55      | PC        | PC            | 1.000000
```

## Implementation in Code

### Item Model
```python
class Item(models.Model):
    unit_id = models.IntegerField()  # References units.unit_id
    # DON'T store base_unit/purchase_unit separately - derive from units table
```

### Units Service Usage
```python
from inventory.services.units_service import UnitsService

# Get display name for UI
display_name = UnitsService.get_purchase_unit_display(unit_id=1)  # "2 KG"

# Convert for recipe calculations  
base_amount = UnitsService.convert_purchase_to_base(
    quantity=1.5,  # 1.5 bags of "2 KG" 
    unit_id=1
)  # Returns 3000.0 GM (1.5 × 2000)

# Convert back for display
purchase_amount = UnitsService.convert_base_to_purchase(
    base_quantity=3000.0,  # 3000 GM
    unit_id=1 
)  # Returns 1.5 (3000 ÷ 2000) bags of "2 KG"
```

## Use Cases

### Recipe Management
- **Input**: User adds "1.5 bags of flour" to recipe
- **Storage**: Convert to base_unit: `1.5 × 2000 = 3000 GM`
- **Calculation**: Recipe uses consistent gram amounts
- **Display**: Show as "1.5 × 2 KG" to user

### Inventory Tracking
- **Purchase**: Buy "5 bags of 2 KG flour" 
- **Storage**: Track as `5 × 2000 = 10000 GM` internally
- **Display**: Show as "5.0 × 2 KG" in UI
- **Reorder**: Alert when below threshold in purchase units

### Cost Calculations
- **Purchase Price**: $10 per "2 KG bag"
- **Unit Cost**: $10 ÷ 2000 GM = $0.005 per GM
- **Recipe Cost**: 500 GM × $0.005 = $2.50

## Benefits

1. **Flexibility**: Same base_unit can have multiple purchase_unit options
2. **Consistency**: All calculations use standardized base_unit amounts  
3. **Accuracy**: Automatic conversions prevent manual calculation errors
4. **User-Friendly**: Display matches real-world purchasing terminology
5. **Scalability**: Easy to add new purchase units without changing recipes

## Migration Notes

### From Current Implementation
The application currently has mixed usage:
- ✅ **Correct**: Items reference `unit_id` 
- ❌ **Incorrect**: Some forms/services store separate `base_unit`/`purchase_unit` fields
- ❌ **Missing**: Conversion factor logic not used consistently

### Required Changes
1. Remove duplicate `base_unit`/`purchase_unit` fields from Item model
2. Use `UnitsService` for all unit operations
3. Update forms to select `unit_id` instead of separate units
4. Implement conversion logic in recipe calculations
5. Update display logic to show `purchase_unit` consistently

## Testing Strategy

The test environment includes fallback unit data:
```python
fallback_units = {
    1: {'base_unit': 'GM', 'purchase_unit': '2 KG', 'conversion_factor': 2000.0},
    19: {'base_unit': 'GM', 'purchase_unit': 'KG', 'conversion_factor': 1000.0}, 
    55: {'base_unit': 'PC', 'purchase_unit': 'PC', 'conversion_factor': 1.0},
}
```

Tests should use `unit_id=19` for "KG" expectations, not `unit_id=1` which returns "2 KG".
