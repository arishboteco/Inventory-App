# Inventory-App Go-Live Checklist And Deployment Plan

Last reviewed: 2026-05-28

## Go/No-Go Rule

Go only when all P0 workflows pass automated checks and local or staging browser UAT, no major page returns a server error, migrations are verified against the target database, and remaining risks are documented as P1/P2 or owner-confirmation items.

Current recommendation before completing browser UAT: **No-go for production cutover**. Draft PRs #853 and #854 reduce known code and UX risk, but owner/business confirmation and manual end-to-end workflow evidence are still required before production cutover.

## 1. Code Freeze

- Freeze feature changes except release-blocker fixes.
- Merge only reviewed, focused branches into `feature/django-refactor`.
- Require every release-blocker fix to include a regression test where practical.
- Run focused validation before each release-branch merge.
- Keep secrets in environment variables only; do not commit credentials or exported production data.

## 2. Staging Deployment

- Deploy the latest `feature/django-refactor` release candidate to staging.
- Confirm environment variables:
  - `DJANGO_SECRET_KEY`
  - `DATABASE_URL`
  - `DJANGO_DEBUG=False`
  - `DJANGO_ALLOWED_HOSTS`
  - `DATABASE_SSL_REQUIRE` if required by the provider
  - static/media storage settings
- Confirm static assets are built with `npm run build`.
- Smoke-test `/healthz`, `/`, `/items/`, `/suppliers/`, `/recipes/`, `/indents/`, `/purchase-orders/`, `/grns/`, `/stock-movements/`, `/stock-takes/`, and `/vendor-prices/`.

## 3. Database Backup And Migration Verification

- Take a database backup immediately before production deployment.
- Record backup location, timestamp, and restore owner.
- Run migrations through Django deployment tooling, not manual table patches.
- Verify expected production tables and columns exist, including:
  - `sales_transactions`
  - `savings_ledger`
  - `vendor_item_prices`
  - `chef_bulletins`
  - `trial_recipe_versions`
  - `recovery_actions`
  - `goods_received_notes.grn_number`
- Run read-only SQL checks in the production database after migration.
- Do not run destructive migrations unless the owner has approved a tested rollback path.

## 4. Seed And QA Data Cleanup

- Use only `QA` or `CODX` prefixes for manual UAT records.
- Before go-live, remove or deactivate QA records from staging or production-like data:
  - Items
  - Suppliers
  - Recipes
  - Indents
  - Purchase orders
  - GRNs
  - Stock transactions
  - Stock takes
  - Vendor prices
- Do not delete records that are linked to transactions unless the app explicitly supports safe deletion. Prefer deactivation or a database restore on disposable staging data.

## 5. Automated Quality Gate

Run from the project root:

```powershell
.\.venv\Scripts\python.exe manage.py check --settings=inventory_app.settings.test
.\.venv\Scripts\python.exe -m pytest tests\test_purchase_order_drawer_partial.py tests\test_purchase_order_service_django.py tests\test_goods_receiving_service_django.py tests\test_stock_service_django.py tests\test_stock_forms.py tests\test_stock_take_workflow.py tests\test_indent_forms.py tests\test_indent_issue_service.py tests\test_recipe_drawer.py tests\test_item_form.py tests\test_items_filters.py tests\test_supplier_form.py -q
.\.venv\Scripts\python.exe -m pytest tests\test_global_usability_accessibility.py tests\test_supplier_form.py tests\test_items_table_accessibility.py tests\test_ui_authenticated_smoke.py -q
npm.cmd test -- modal-po-validation.test.js recipe-components.test.js predictive-dropdown.test.js forms-validation.test.js notifications.test.js column-filters.test.js items-table.test.js --runInBand
```

Before final release, run `make ci` or document any unrelated known failures with exact failing tests.

## 6. Smoke Test Checklist

- Login succeeds with the intended owner/admin account.
- Navigation groups render: Insights, Procurement, Stock, Master Data.
- No major page returns HTTP 500.
- Drawers open and close consistently for item, supplier, recipe, indent, PO, receiving, and stock movement forms.
- Required fields show visible markers and actionable validation messages.
- Destructive actions require confirmation.
- Toasts show plain English without HTML entities.
- CSV exports download for Items, Suppliers, POs, and any implemented stock/GRN exports.
- Logout ends the session and browser back does not restore private screens.

## 7. Full UAT Checklist

Complete the QA matrix in `docs/production-readiness/qa-matrix.md` and attach evidence for these eight workflows:

1. Create item -> update item -> receive stock -> adjust stock -> stock movement appears.
2. Create supplier -> link supplier to item/vendor price -> create PO.
3. Create recipe -> request ingredients -> create indent.
4. Approve indent -> consolidate/order plan -> create PO.
5. Receive PO -> GRN created -> item stock updated -> PO status updated.
6. Create stock take -> enter count -> review variance -> complete -> stock adjusted.
7. Record wastage -> stock reduces -> wastage transaction appears.
8. Transfer stock -> source/destination department movement appears.

## 8. Rollback Plan

- Keep the previous production image/release available.
- Keep the pre-deploy database backup available and restore-tested.
- If deployment fails before migrations, roll back application release only.
- If deployment fails after migrations, assess whether migrations are backward compatible:
  - If compatible, roll back application release and keep migrated database.
  - If not compatible, restore the database backup and roll back application release together.
- Record the incident timeline, failed health checks, logs, and owner decision.

## 9. Monitoring, Logging, And Error Tracking

- Monitor HTTP 500s, login failures, migration errors, and slow requests.
- Watch workflows with stock impact: GRNs, stock movements, indent issue, and stock take completion.
- Confirm logs do not expose secrets, passwords, or full credential strings.
- Configure alerting for repeated server errors and failed deployment health checks.
- Review stock transaction anomalies daily during hypercare.

## 10. User Access, Roles, And Training

- Confirm user groups map to app roles:
  - Owner
  - Purchase
  - Storekeeper
  - Head Chef
  - Kitchen Staff
- Confirm unauthorized users cannot mutate restricted workflows.
- Prepare short training notes for:
  - Creating items and suppliers
  - Creating and approving indents
  - Consolidating approved indents into POs
  - Receiving goods and checking GRNs
  - Recording wastage, adjustments, and transfers
  - Running stock takes
  - Reading owner dashboards and recovery actions

## 11. Known Limitations Requiring Owner Confirmation

- Whether ad-hoc GRNs without POs are allowed in production.
- Whether negative stock is ever allowed and who can override it.
- Whether same-day duplicate PO generation from consolidation should be blocked or warned.
- Whether completed stock takes can ever be reopened.
- Whether delete actions should hard-delete, soft-delete, or deactivate linked records.
- Whether vendor prices are a read-only comparison tool or full CRUD master data for procurement.

## 12. Production Deployment Steps

1. Announce code freeze and maintenance window.
2. Confirm latest release candidate commit and tag.
3. Take and verify database backup.
4. Deploy application release.
5. Run Django migrations.
6. Build and collect static assets if required by the platform.
7. Run health check.
8. Run smoke checklist.
9. Run critical workflow UAT with QA/CODX data.
10. Remove QA/CODX data or restore clean staging copy as appropriate.
11. Announce go-live or rollback decision.

## 13. Seven-Day Hypercare

| Day | Activity |
| --- | --- |
| Day 0 | Monitor deploy, login, page load, and P0 workflows continuously for the first business cycle. |
| Day 1 | Review stock transactions, GRNs, PO statuses, and failed form submissions. |
| Day 2 | Validate owner dashboard numbers against expected operational data. |
| Day 3 | Review user feedback and fix P0/P1 issues only. |
| Day 4 | Audit imports/exports and cleanup any accidental QA records. |
| Day 5 | Review role permissions and destructive-action logs. |
| Day 6 | Prepare post-launch bug list and training clarifications. |
| Day 7 | Owner sign-off, decide whether to reopen feature work, and archive hypercare evidence. |
