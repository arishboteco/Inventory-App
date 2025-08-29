Legacy Supabase Services
========================

This folder contains transitional Supabase service modules kept for backward compatibility
during the migration to pure Django ORM services.

Behavior:
- Controlled by the LEGACY_SUPABASE environment variable (default: enabled).
- When disabled (LEGACY_SUPABASE=false), Supabase clients resolve to None and callers fall back.
- Tests that mock Supabase will still pass with LEGACY_SUPABASE enabled.

Modules:
- supabase_client.py
- supabase_categories.py
- supabase_units.py

Plan:
- Migrate consumers to ORM-based services in categories/units.
- Eventually remove this folder when no longer needed.
