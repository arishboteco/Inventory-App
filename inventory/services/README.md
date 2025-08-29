Service Layer Overview
======================

This package contains all business logic for the Inventory App. Views should be HTTP-only
and delegate business rules, formatting, and data access to services in this folder.

Key points:
- Prefer Django ORM services over legacy Supabase ones.
- Use `item_service.get_unit_display_name(unit_id)` for unit labels.
- Keep imports at module scope; move logic into services to avoid circulars.

Legacy Supabase
---------------
- Legacy Supabase modules are in `inventory/services/_legacy`.
- Controlled by `LEGACY_SUPABASE` environment variable.
  - Default: enabled (tests expect legacy to be available).
  - Disable with: `LEGACY_SUPABASE=false` (client returns None; callers should fall back).

Transition plan:
- Gradually migrate consumers to ORM-based services (`categories_service`, `units_service`).
- Remove `_legacy` after all consumers are migrated and tests updated.
