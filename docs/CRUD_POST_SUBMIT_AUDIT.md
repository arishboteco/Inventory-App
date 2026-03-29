# CRUD / post-submit audit

Generated as part of the systematic audit (March 2026). Use this with [inventory/ui_urls.py](../inventory/ui_urls.py) and [inventory_app/navigation.py](../inventory_app/navigation.py).

## Interaction types

| Type | Meaning | Client behavior |
|------|---------|-----------------|
| **FullPageForm** | Normal `<form>` POST | Browser follows redirect or renders full HTML |
| **DrawerOrModal_JSON** | Form has `data-modal-form` | [static/js/modal.js](../static/js/modal.js) `fetch()` + JSON; may `window.location` on `redirect` |
| **HTMX** | `hx-get` / `hx-post` | Partial swap into target |
| **fetch_only** | JS `fetch()` without modal attribute | Expect JSON; no full navigation unless handled in JS |

## Navigation vs routes

All primary nav targets from `NAVIGATION_GROUPS` resolve to names in `ui_urls.py`. Additional high-traffic UI not in the slim nav: `item_detail`, `item_edit`, `purchase_order_detail`, `purchase_order_receive`, `indent_detail`, `grn_detail`, `recipe_detail`, `workflow_guide`, `settings`, `profile-edit`, `change-password`.

## POST / submit matrix (high-value flows)

| Area | Action | URL name | Interaction | Success outcome | Failure / notes |
|------|--------|----------|-------------|-----------------|-----------------|
| Items | List / filter | `items_list`, `items_table` | HTMX (table) | Swap `#items-list` | — |
| Items | Create (drawer) | `item_create_partial` → POST `items_list` | Drawer JSON | JSON `ok`, reload per modal.js | Partial must include `data-modal-form` |
| Items | Edit (drawer) | `item_edit` `?partial=1` | Drawer JSON | JSON / redirect per view | — |
| Items | Inline update | `item_inline_update` | fetch_only | JSON | Hardcoded `/items/<id>/inline-update/` in JS |
| Items | Bulk actions | `items_bulk_update` | fetch_only | JSON + `window.location.reload()` | — |
| Items | Bulk upload drawer | `items_bulk_upload` `?partial=1` | Drawer JSON | Per `ItemsBulkUploadView` | `_bulk_upload_partial.html` |
| Stock | Receive (modal) | `stock_movements` + `submit_receive` | FullPageForm | `redirect("stock_movements")` | `_receive_form_modal.html`: `action=""` — not `data-modal-form` |
| Stock | Adjust / waste / transfer modals | `stock_movements` | FullPageForm | Redirect + `?section=...` on errors; PRG flash | Same pattern |
| Stock | Bulk CSV modal | `stock_movements` | FullPageForm | Posts to same view | `_stock_bulk_modal.html` |
| PO | Create / edit drawer | `purchase_order_create_partial`, `purchase_order_edit_partial` | Drawer JSON | JSON | `data-requires-line-items` |
| PO | Receive drawer | `purchase_order_receive_partial` | Drawer JSON | JSON `redirect` → PO detail | `data-modal-form` |
| PO | Mark ordered | `purchase_order_mark_ordered` | FullPageForm | Redirect detail | Full page on PO detail |
| Indents | Create drawer | `indent_create` `?partial=1` | Drawer JSON | JSON | — |
| Indents | Update (drawer) | `indent_update` | Drawer JSON | — | `_indent_detail_partial.html` |
| Indents | Status buttons in drawer | `indent_update_status` | FullPageForm (inline forms) | Redirect | Small forms without `data-modal-form` — POST goes to named URL (full page) |
| Indents | Consolidate | `indents_consolidate_preview` | FullPageForm | Redirect PO list / same page | — |
| GRN | Create / adhoc | `grn_create`, `grn_create_adhoc` | FullPageForm | Redirect / render | — |
| Recipes | Create / edit drawer | `recipe_create_partial`, `recipe_edit_partial` | Drawer JSON | JSON | — |
| Recipes | Request ingredients | `recipe_create_indent` | FullPageForm | `redirect("indent_detail")` | Form in `_view_partial.html` has **no** `data-modal-form` — intentional full navigation to indent |
| Recipes | Delete | `recipe_delete` | POST (modal flow) | Redirect list | — |
| Suppliers | Create / edit drawer | `supplier_create`, `supplier_edit` `?partial=1` | Drawer JSON | JSON | List uses `data-modal-url` to `supplier_create` — form partial supplies `data-modal-form` |
| Suppliers | Bulk upload | `suppliers_bulk_upload_partial` | Drawer JSON | JSON | — |
| Stock take | Start / count / review | `stock_take_*` | FullPageForm | Redirect / render | — |
| Settings / profile | Various | `settings`, `profile-edit`, `change-password` | FullPageForm | Redirect / render | — |

## Pattern grep — `data-modal-form` coverage

Templates **with** `data-modal-form` (drawer JSON path):  
`recipes/_form_partial.html`, `purchase_orders/_receive_partial.html`, `purchase_orders/_form_partial.html`, `_supplier_form_partial.html`, `_item_create_partial.html`, `_item_form_partial.html`, `_indent_create_partial.html`, `_bulk_upload_partial.html`, `_indent_detail_partial.html` (main update form only), `_item_create_bare.html`.

See [drawer_modal_htmx_migration.md](drawer_modal_htmx_migration.md) for a full inventory and HTMX migration notes.

**Native modals on stock** (`action=""`, no `data-modal-form`):  
`_receive_form_modal.html`, `_adjust_form_modal.html`, `_waste_form_modal.html` — rely on current page URL being `/stock-movements/`.

## Hardcoded root-relative URLs in JS (subpath risk)

If the app is mounted under a subpath (`FORCE_SCRIPT_NAME`), these may 404 while `{% url %}` works:

| File | Paths |
|------|--------|
| [static/js/items-table.js](../static/js/items-table.js) | `/items/<id>/inline-update/`, `/items/<id>/delete/`, `/items/<id>/toggle/`, `/items/bulk/`, `/items/table/`, `/items/export/` |
| [static/js/indent-form.js](../static/js/indent-form.js) | `/items/meta/<id>/` |
| [static/js/recipe-components.js](../static/js/recipe-components.js) | `/recipes/meta/...`, `/items/meta/...` |
| [static/js/smart-forms.js](../static/js/smart-forms.js) | `/items/check-similar-names/`, `/items/<id>/` |
| [static/js/column-filters.js](../static/js/column-filters.js) | `/items/distinct/...`, `/items/table/` |
| [templates/inventory/stock_movements.html](../templates/inventory/stock_movements.html) (inline script) | `/items/meta/<id>/` |

## “Restock” flows (terminology)

There is no `restock` label in code. Closest flows:

1. **Receive Stock** (Stock Movements modal): native POST → `302` → `/stock-movements/`. Verified by automated test `test_stock_receive_native_post_redirects_to_full_stock_movements`.
2. **Items table**: edit **Stock** column → `fetch` POST `item_inline_update` → JSON (no navigation).
3. **PO Receive** (drawer): `fetch` → JSON with `redirect` to PO detail.

## Automated verification

See [tests/test_crud_post_submit_audit.py](../tests/test_crud_post_submit_audit.py) for:

- Stock receive POST redirect chain (no dead-end partial document).
- PO receive partial XHR JSON + `redirect` key.
- Item inline stock update JSON (restock-style inline).

Run: `pytest tests/test_crud_post_submit_audit.py -q`

## Manual checklist (when debugging a report)

1. Open DevTools → Network → submit the form.
2. Note: POST URL, status code, `Content-Type`, `Location` (if redirect).
3. **Dead-end partial**: response is 200 `text/html` fragment without layout, URL path contains `partial` or looks like a drawer endpoint.
4. **Expected JSON**: `application/json` body with `ok` / `redirect` / `message`.
