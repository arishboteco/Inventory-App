Service Layer Overview
======================

This package contains all business logic for the Inventory App. Views should be HTTP-only
and delegate business rules, formatting, and data access to services in this folder.

Key points:
- Services use the Django ORM exclusively.
- Use `item_service.get_unit_display_name(unit_id)` for unit labels.
- Keep imports at module scope; move logic into services to avoid circulars.
- Categories and units data come from `categories_service` and `units_service`.

Caching
-------

Read-heavy service helpers use Python's built-in `functools.lru_cache` for
in-process caching. Each cached function exposes a `.clear()` method (alias of
`cache_clear`) to invalidate results after any write operation.

Example:

```python
from inventory.services.stock_utils import get_low_stock_items

items = get_low_stock_items()  # First call queries the database
get_low_stock_items.clear()    # Clear cache after stock updates
```
