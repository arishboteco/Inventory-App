# Copilot Instructions for Inventory-App

## Project Overview
Django 5.2.5 restaurant inventory management system with PostgreSQL, migrated from Supabase. Features real-time stock tracking, purchase orders, recipe management, and ML-driven analytics.

## Architecture Patterns

### Service Layer Architecture
Business logic lives in `inventory/services/` with single-responsibility services:
- `item_service.py` - Item CRUD, unit resolution, display formatting
- `dashboard_service.py` - KPI calculations, low-stock alerts
- `form_service.py` - Dropdown population, category/unit choices
- `stock_service.py` - Stock movements, adjustments, wastage tracking

Always use services for business logic. Views should only handle HTTP concerns.

### Model Organization
Models split by domain in `inventory/models/`:
- `items.py` - Item, StockTransaction
- `orders.py` - PurchaseOrder, Indent, GRN entities
- `recipes.py` - Recipe, RecipeComponent, SaleTransaction
- `departments.py` - Department, ItemDepartment (many-to-many)

Import models from `inventory.models` (uses `__init__.py` exports).

### Form System with StyledFormMixin
All forms inherit `StyledFormMixin` from `inventory/forms/base.py`:
```python
class ItemForm(StyledFormMixin, forms.ModelForm):
    # Automatically applies Tailwind classes and 'predictive' to selects
```
The mixin adds `predictive` class to select widgets for JavaScript enhancement.

## Development Workflows

### Essential Commands
```bash
# Run tests (uses pytest with Django settings)
make test

# Format and lint (Black + Ruff)
make fmt && make lint

# Build CSS and collect static files
npx tailwindcss -i ./static/src/app.css -o ./static/css/app.css --minify
python manage.py collectstatic --noinput

# Database migrations
python manage.py makemigrations
python manage.py migrate
```

### Testing Strategy
- Test files in `tests/` directory with `test_*.py` naming
- Use `pytest` with Django test database reuse (`--reuse-db`)
- Current coverage: 99.1% (112/113 tests passing)
- Run `pytest` not `python manage.py test`

## UI & Frontend Patterns

### Tailwind CSS Strategy
Desktop-first approach with `max-*` variants for mobile:
```html
<div class="grid grid-cols-4 max-md:grid-cols-1">
```

Design tokens in `static/src/tokens.css` → `tailwind.config.js`. Update tokens file for global color changes.

### Predictive Dropdowns
Any `<select class="predictive">` gets enhanced with search functionality. Forms using `StyledFormMixin` get this automatically.

### JavaScript Modules
- `static/js/dynamic-units.js` - Unit dependency management
- `static/js/smart-forms.js` - Form enhancements
- `static/js/smart-navigation.js` - Navigation helpers

## Data Flow & Integration

### Unit System
Complex unit relationships with base_unit → purchase_unit mappings:
- Use `FormService.get_unit_choices()` for dropdowns
- `item_service.get_unit_display_name()` for consistent formatting
- Dynamic unit loading via AJAX endpoints

### URL Structure
Dual URL pattern:
- `inventory/urls.py` - API endpoints
- `inventory/ui_urls.py` - HTML views
Both included in main URLconf.

### Environment Configuration
Multi-environment setup:
- `inventory_app/settings.py` - Development
- `inventory_app/settings_production.py` - Production
- `inventory_app/settings_staging.py` - Staging
- `inventory_app/settings_test.py` - Testing

Uses `django-environ` for environment variables.

## Key Conventions

### Code Quality
- Python 3.13 target (`pyproject.toml`)
- Black formatting (88 char line length)
- Ruff linting with auto-fix
- Run `flake8` and `pytest` before commits

### Performance Patterns
- Use `only()` and `select_related()` in querysets
- Service layer caching with `@lru_cache`
- Optimized templates for fast rendering

### Error Handling
Custom middleware in `core/middleware.py` for login enforcement and error logging.

## Migration Context
Recently migrated from Supabase to Django models. Some services still have legacy Supabase integration (`supabase_*.py`) for transition period. Prefer Django ORM patterns for new code.

## Common Pitfalls
- Don't bypass the service layer for business logic
- Always use `StyledFormMixin` for forms
- Use `item_service.get_unit_display_name()` not direct unit_id access
- Test with both empty and populated databases due to unit resolution complexity
