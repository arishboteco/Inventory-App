# Phase 10 Release Checklist

Use this checklist before merging to the main integration branch and before deploying to Supabase-backed environments.

## 1) Local Quality Gate

- Run system checks:
  - `.\.venv\Scripts\python.exe manage.py check --settings=inventory_app.settings.test`
- Run focused regression tests:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_phase10_smoke.py tests\test_modal_scroll_layout.py tests\test_purchase_order_drawer_partial.py tests\test_navigation.py -q`
- Run key flow tests:
  - `.\.venv\Scripts\python.exe -m pytest tests\test_recovery_pages.py tests\test_pos_sales_import.py tests\test_variance_report_view.py tests\test_chef_bulletins_views.py tests\test_recovery_actions_views.py -q`
- Run lint on changed files:
  - `.\.venv\Scripts\python.exe -m ruff check inventory/forms/base.py inventory/management/commands/seed_dashboard_data.py tests/test_phase10_smoke.py tests/test_modal_scroll_layout.py tests/test_purchase_order_drawer_partial.py`

## 2) Demo Data Gate

- Seed the app:
  - `.\.venv\Scripts\python.exe manage.py seed_dashboard_data --days 30 --settings=inventory_app.settings.dev`
- Confirm generated records exist for:
  - POS sales (`sales_transactions`)
  - POS mapping (`pos_menu_item_mappings`)
  - vendor prices (`vendor_item_prices`)
  - savings ledger (`savings_ledger`)
  - chef bulletins (`chef_bulletins`)
  - recovery actions (`recovery_actions`)

## 3) Manual UI Gate

- Log in as Owner and verify navigation includes:
  - Insights, Procurement, Stock, Master Data
- Confirm these pages load and are usable:
  - `/`, `/items/`, `/suppliers/`, `/recipes/`, `/purchase-orders/`, `/grns/`, `/stock-movements/`, `/savings-ledger/`, `/vendor-prices/`, `/pos-sales/`, `/variance-report/`, `/chef-bulletins/`, `/recovery-actions/`
- Check modal/drawer behavior:
  - Drawer forms scroll on smaller screens.
  - Purchase Order notes field appears as a full-width row below the two-column field grid.
  - Date fields show native date pickers and also accept manual entry formats handled by the backend.

## 4) Migration Gate (Supabase/Prod)

Run Django migrations from the app deployment path; do not patch tables manually.

- Confirm migration state includes:
  - `sales_transactions`
  - `savings_ledger`
  - `vendor_item_prices`
  - `chef_bulletins`
  - `trial_recipe_versions`
  - `recovery_actions`
  - `goods_received_notes.grn_number`

Suggested verification SQL (read-only):

```sql
select table_name
from information_schema.tables
where table_schema='public'
  and table_name in (
    'sales_transactions',
    'savings_ledger',
    'vendor_item_prices',
    'chef_bulletins',
    'trial_recipe_versions',
    'recovery_actions'
  )
order by table_name;
```

```sql
select column_name
from information_schema.columns
where table_schema='public'
  and table_name='goods_received_notes'
  and column_name='grn_number';
```

## 5) Release Sign-off

- CI green (lint + tests).
- Manual UI gate completed.
- Migration gate completed in target Supabase environment.
- Owner dashboard numbers reviewed after seed or production data refresh.
