Service Layer Overview
======================

This package contains all business logic for the Inventory App. Views should be HTTP-only
and delegate business rules, formatting, and data access to services in this folder.

Key points:
- Services use the Django ORM exclusively.
- Use `item_service.get_unit_display_name(unit_id)` for unit labels.
- Keep imports at module scope; move logic into services to avoid circulars.
- Categories and units data come from `categories_service` and `units_service`.
