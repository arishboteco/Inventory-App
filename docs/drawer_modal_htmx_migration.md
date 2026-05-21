# Drawer (`data-modal-form`) inventory and HTMX follow-ups

## Todo 7 — Inventory: `data-modal-form` endpoints (complete list)

Forms intercepted by `static/js/modal.js` (`fetch` POST, `partial=1`, JSON success; structured `errors` on 400 from `build_form_error_payload` where implemented).

| Template                                          | POST action (URL name / pattern)                               | Notes                                              |
| ------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------- |
| `inventory/purchase_orders/_form_partial.html`    | `purchase_order_create_partial`, `purchase_order_edit_partial` | `data-formset-prefix`; `initPurchaseOrderDrawer`   |
| `inventory/purchase_orders/_receive_partial.html` | `purchase_order_receive_partial`                               | `multipart/form-data`; line qty validation         |
| `inventory/recipes/_form_partial.html`            | `recipe_create_partial`, `recipe_edit_partial`                 | `data-formset-prefix`; `initRecipeComponentsTable` |
| `inventory/_supplier_form_partial.html`           | `supplier_create`, `supplier_edit`                             | `?partial=1`                                       |
| `inventory/_item_form_partial.html`               | `item_edit`                                                    | `?partial=1`                                       |
| `inventory/_item_create_partial.html`             | `items_list`                                                   | Item create drawer                                 |
| `inventory/_item_create_bare.html`                | `items_list`                                                   | Bare / inline create                               |
| `inventory/_indent_create_partial.html`           | `indent_create`                                                | `initIndentForm`, line items                       |
| `inventory/_indent_detail_partial.html`           | `indent_update`                                                | Edit indent in drawer                              |
| `inventory/_bulk_upload_partial.html`             | `{{ upload_url }}`, `upload_csv?partial=1`                     | Two forms; multipart                               |

**Client hub:** `static/js/modal.js` — delegated `submit` on `[data-modal-form]`; summary + per-field highlights for `errors` matching `build_form_error_payload`.

**Init hooks after `innerHTML` (drawer open):** `initIndentForm`, `initRecipeComponentsTable`, `initRecipeYieldUnitRoots`, `initPurchaseOrderDrawer`, predictive dropdowns, multiselect chips, `htmx.process`.

## Todo 7 — Migration strategy (HTMX)

1. Do **not** migrate a single flow in isolation; pick a **cluster** (e.g. PO create/edit + receive, or items + suppliers).
2. Target pattern: `hx-post` on the form, `hx-target` / `hx-swap` for error HTML, `HX-Redirect` or `HX-Trigger` on success; move behaviors to `htmx:afterSwap` initializers instead of inline `<script>` in partials.
3. Until migration, keep **one JSON error shape** (`build_form_error_payload` and friends) for remaining `modal.js` forms.

## Quick PO (removed)

Single entry: **New Purchase Order** drawer (`purchase_order_create_partial`). List helper describes supplier, dates, and line items.

## Todo 8 — PO service symmetry

- **Single valid path:** `purchase_order_service.save_purchase_order_from_forms(form, formset)` — create delegates to `create_po`; update uses `form.save()` + `formset.save()` (stable line PKs for GRNs / indents).
- **Direct `create_po`** remains for programmatic callers (e.g. indent consolidation, tests, goods receiving fixtures).

## Todo 9 — Backlog (explicit out of scope for PO drawer work)

Track as separate tickets when prioritized:

- **PO Receive / GRN / consolidation:** Align validation JSON or HTMX with the same patterns as PO create where it reduces user confusion.
- **Schema:** New `PurchaseOrder` / `PurchaseOrderItem` migrations only when product requires them.
- **Full-page PO form:** Further deduplication with drawer partial (shared includes for lines where practical).
- **E2E:** Playwright (or similar) smoke for drawer open → add line → save, if CI budget allows.
