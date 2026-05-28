# Inventory-App Route And Process Audit

Last reviewed: 2026-05-28
Target branch: `feature/django-refactor`
Documentation branch: `feature/prod-readiness-audit-docs`

## Summary

Inventory-App is a Django 5.2 application with HTML UI routes in `inventory/ui_urls.py`, API routes in `inventory/urls.py`, and navigation in `inventory_app/navigation.py`. Business logic is concentrated in `inventory/services/`; forms live in `inventory/forms/`; UI templates live under `templates/inventory/` and shared components under `templates/components/`.

## Core, Auth, And Admin

| Route | Area | View | Process | Readiness notes |
| --- | --- | --- | --- | --- |
| `/` | Insights dashboard | `core.views.root_view` | Owner dashboard, KPIs, alerts, trends | Smoke-load before release; verify role-scoped navigation. |
| `/login/`, `/accounts/login/` | Auth | Django auth views | Login/session start | UAT with QA account only; verify failed-login and logout paths. |
| `/accounts/logout/` | Auth | Django auth views | Session end | Verify logout redirects and back button does not restore authenticated state. |
| `/accounts/password-reset-info/` | Auth | `password_reset_info_view` | Password reset guidance | Confirm no credentials or sensitive settings are exposed. |
| `/admin/` | Admin | Django admin | Admin CRUD | Superuser-only; smoke-load and confirm no model admin server errors. |
| `/healthz` | Ops | `health_check` | Runtime health | Use for deployment health checks. |
| `/kpis/`, `/dashboard-data/` | Insights API | `dashboard_kpis`, `ajax_dashboard_data` | Dashboard partial data | Verify JSON/partial responses under authenticated session. |

## Insights

| Route | View/template | Process | Validation or service owner |
| --- | --- | --- | --- |
| `/recipes/food-cost-report/` | `food_cost_report`, `inventory/recipes/food_cost_report.html` | Recipe cost, margin, target food cost review | Recipe model properties and recipe service. |
| `/savings-ledger/` | `savings_ledger_list` | Estimated/confirmed/lost savings review | `SavingsLedger`, vendor savings service. |
| `/recovery-actions/`, `/recovery-actions/<id>/` | `recovery_actions_list`, `recovery_action_detail` | Owner action tracking | `RecoveryActionForm`, recovery action service. |
| `/recovery-actions/<id>/status/` | `recovery_action_status` | Status update | `RecoveryActionStatusForm`; verify role rules. |
| `/pos-sales/` | `pos_sales_import` | POS import and recipe mapping | `POSSalesImportForm`, POS sales import service. |
| `/variance-report/` | `variance_report` | Ideal vs actual stock variance | `variance_service.build_variance_report`. |
| `/chef-bulletins/`, `/chef-bulletins/<id>/` | Chef bulletin views | Recipe alerts and detail | Chef bulletin service. |
| `/chef-bulletins/<id>/decision/` | `chef_bulletin_decision` | Accept/reject/trial decision | Verify status, trial recipe, and recovery action impact. |
| `/history-reports/` | `history_reports` | Stock audit trail | Stock transaction filters. |
| `/visualizations/` | `visualizations` | Stock charts | Verify filters and chart data. |
| `/ml-dashboard/` | `ml_dashboard` | Reorder suggestions | ML service/cache; confirm helpful empty state. |

## Master Data

| Route | View/template | Process | Validation or service owner |
| --- | --- | --- | --- |
| `/items/`, `/items/table/` | `ItemsListView`, `ItemsTableView`, item table templates | List, search, filters, sorting, pagination, table actions | `inventory/views/items/list.py`, `list_utils`. |
| `/items/create/`, `/items/create/partial/` | `ItemCreateHTMXView`, `ItemCreatePartialView` | Add item drawer/fallback | `ItemForm`; verify name/unit required, category and reorder point persistence. |
| `/items/<id>/edit/` | `ItemEditView` | Update item | `ItemForm`; verify departments, preferred supplier, active flag. |
| `/items/<id>/duplicate/` | `ItemDuplicateView` | Prefill a new item from existing data | Confirm it does not save until submitted. |
| `/items/<id>/delete/` | `ItemDeleteView` | Delete or deactivate safely | Protect linked transaction history. |
| `/items/<id>/toggle/` | `ItemToggleActiveView` | Activate/deactivate | Confirm list filters reflect state. |
| `/items/export/`, `/items/upload/`, `/items/bulk-upload/` | Export/upload views | CSV import/export | Verify headers, validation errors, and QA data cleanup. |
| `/items/search/`, `/items/meta/<id>/`, `/items/distinct/<field>/` | Lookup endpoints | Autocomplete/filter metadata | Verify empty and filtered responses. |
| `/suppliers/`, `/suppliers/table/`, `/suppliers/cards/` | Supplier list views | List, search, status, view mode, columns, pagination | `SupplierForm`, `supplier_service`, `list_utils`. |
| `/suppliers/create/`, `/suppliers/<id>/edit/` | Supplier drawer views | Create/update supplier | Required fields: name and contact person; no fake phone/email defaults. |
| `/suppliers/<id>/toggle/`, `/suppliers/<id>/delete/` | Supplier action views | Activate/deactivate/delete | Delete is blocked when open POs exist; linked-data behavior needs UAT. |
| `/suppliers/bulk-upload/`, `/suppliers/bulk-delete/` | Bulk supplier views | CSV load/deactivation | Verify confirmation and error reporting. |
| `/suppliers/search/` | `SupplierSearchView` | Supplier autocomplete | Active suppliers only, partial name friendly. |
| `/recipes/`, `/recipes/table/` | Recipe list views | List, search, filters, sorting | `RecipeForm`, `RecipeItemFormSet`, recipe service. |
| `/recipes/create/`, `/recipes/create/partial/` | Recipe create views | Create recipe with ingredients/sub-recipes | Require at least one positive ingredient row. |
| `/recipes/<id>/edit/partial/` | `RecipeEditPartialView` | Edit recipe and line items | Hidden ingredient ids must render; unchanged unique name must not fail duplicate check. |
| `/recipes/<id>/view/partial/`, `/recipes/<id>/` | Recipe detail views | Read recipe costing and components | Verify cost breakdown and zero-cost warnings. |
| `/recipes/<id>/create-indent/` | `recipe_create_indent` | Request ingredients from a recipe | Verify quantities and indent status. |
| `/recipes/<id>/delete/` | `RecipeDeleteView` | Delete recipe | Confirm linked sales/sub-recipe protection. |

## Procurement

| Route | View/template | Process | Validation or service owner |
| --- | --- | --- | --- |
| `/indents/`, `/indents/table/` | Indent list/table views | List, filters, status, overdue, pagination | `IndentForm`, `IndentItemFormSet`. |
| `/indents/create/` | `IndentCreateView` | Create request | Department required; at least one positive item required. |
| `/indents/<id>/`, `/indents/<id>/update/` | Detail/update views | Read/edit when allowed | Verify impossible transitions are blocked. |
| `/indents/<id>/status/<status>/` | `indent_update_status` | Approve/reject/cancel/process | Verify valid status graph only. |
| `/indents/<id>/issue/` | `issue_indent` | Fulfil/issue stock | `indent_issue_service`; blocks over-issue and reduces stock. |
| `/indents/<id>/pdf/` | `indent_pdf` | Print/export | Verify PDF response and permissions. |
| `/indents/generate-from-low-stock/` | `generate_low_stock_indent` | Create indent from low stock | Verify reorder point logic and duplicate prevention. |
| `/indents/consolidate/preview/` | `consolidate_indents` | Order planner preview | `indent_consolidation_service`; groups approved lines by supplier. |
| `/indents/consolidate/` | `indents_consolidate` | Generate POs | Verify no duplicate PO lines and correct indent links. |
| `/purchase-orders/`, `/purchase-orders/table/`, `/purchase-orders/cards/` | PO list views | Search, filters, view modes, progress, actions | `PurchaseOrderForm`, `PurchaseOrderItemFormSet`. |
| `/purchase-orders/create/partial/` | PO create drawer | Create PO | Supplier, order date, and one valid line required. |
| `/purchase-orders/<id>/edit/partial/` | PO edit drawer | Update PO | Received lines cannot be deleted incorrectly. |
| `/purchase-orders/<id>/mark-ordered/` | `mark_ordered` | Draft to sent | Confirm idempotency and invalid status handling. |
| `/purchase-orders/<id>/receive/partial/` | PO receive drawer | Receive against PO | `goods_receiving_service.create_grn`; blocks over-receipt. |
| `/purchase-orders/export/` | PO export | CSV download | Verify filters are respected. |
| `/grns/`, `/grns/<id>/` | GRN list/detail | Receiving history | Verify GRN number, stock impact, attachments. |
| `/grns/create/`, `/grns/create/adhoc/` | GRN create views | PO and ad-hoc receiving | Confirm ad-hoc receiving is intended before go-live. |
| `/grns/<id>/export/` | GRN export | Download/print | Verify file response. |
| `/vendor-prices/` | `vendor_prices_list` | Vendor price comparison | Confirm CRUD requirements; current route is list/comparison focused. |

## Stock

| Route | View/template | Process | Validation or service owner |
| --- | --- | --- | --- |
| `/stock-movements/` | `stock_movements`, stock movement partials | Receive, adjust, wastage, transfer, bulk upload | `stock_forms.py`, `stock_service.record_stock_transaction`. |
| `/stock/users/search/`, `/stock/pos/search/` | Search views | User and PO autocomplete | Verify partial matching and empty states. |
| `/stock-takes/` | `stock_take_list` | List stock takes | Confirm status display and review action. |
| `/stock-takes/new/` | `create_stock_take` | Start count | Date defaults to today; department optional if all-department count is intended. |
| `/stock-takes/<id>/count/` | `stock_take_count` | Enter physical quantities | Snapshot system quantity and save counts. |
| `/stock-takes/<id>/review/` | `stock_take_review` | Review and complete | Completing creates adjustment transactions for variances. |

## API Surface

The API router exposes CRUD-style endpoints for items, suppliers, stock transactions, indents, indent items, purchase orders, purchase order items, goods received notes, GRN items, recipes, recipe items, sale transactions, and POS menu item mappings. Additional endpoints support item export, item similarity checks, unit/subcategory lookups, and what-if reorder calculations.

## Findings From The 2026-05-28 Pass

- P0 fixes were split into draft PR #853: PO detail receive actions use the drawer partial, PO line price edits update item price history, bulk stock transactions cannot drive negative stock and roll back as a batch, and completed stock takes cannot be discarded by direct POST.
- P1 UX/accessibility fixes were split into draft PR #854: Items column menu, supplier card actions, and the shared action menu now use clearer labels/tooltips/aria labels.
- Existing automated coverage already checks many previously known blockers: item category/reorder persistence, recipe edit hidden ids and duplicate-name handling, indent non-empty requirement, indent issue transaction boundaries, PO supplier search, GRN over-receipt, and stock form validation.
- Remaining go-live risk is operational breadth, not a single known crashing code path: complete local/staging browser UAT must still be run across all critical workflows before production sign-off.
