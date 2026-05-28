# Production Readiness QA Matrix

Use `QA` or `CODX` prefixes for all manual records created during local or staging UAT. Mark each row `Pass`, `Fail`, `Blocked`, or `Not implemented`, and link the exact issue or commit for every failure.

| Page | Feature/Form | Create | Read/View | Update/Edit | Delete/Cancel | Filters/Search | Import/Export | Status transitions | Stock/accounting impact | Result | Notes/Bugs fixed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Dashboard | Overview KPIs and alerts | N/A | Load KPIs, alerts, charts | N/A | N/A | Date/window controls | N/A | N/A | Reads stock, purchase, sales, variance totals | Pending UAT | Verify no server errors and values are plausible. |
| Items | Item CRUD | Add `QA Item` with category, unit, reorder point, supplier, departments | Detail drawer/page opens | Edit all fields | Delete unused item; deactivate linked item | Search, category, subcategory, unit, supplier, department, status, stock status | CSV export and bulk upload | Active/inactive | Reorder point, low-stock status, stock value | Automated partial pass; UAT pending | Existing tests cover reorder point/category persistence. |
| Items | Item table actions | N/A | View icon opens detail | Edit icon opens drawer | Delete/activate/deactivate confirm | Sorting, pagination, columns, compact view | Export filtered CSV | Active/inactive | No stock mutation unless explicit action | Automated partial pass; UAT pending | PR #854 standardizes the column-menu label; browser spot-check still required. |
| Suppliers | Supplier CRUD | Add `QA Supplier` without fake phone/email defaults | Detail drawer opens | Edit contact fields | Delete unused supplier; block/delete linked supplier safely | Search, status, table/cards, columns, compact view | CSV export, bulk upload, bulk delete | Active/inactive | Supplier availability in PO and item forms | Automated partial pass; UAT pending | Required fields: name and contact person; PR #854 improves card action labels. |
| Recipes | Recipe CRUD | Create final recipe and sub-recipe with positive ingredient | Detail/view partial shows costing | Edit ingredient rows and unchanged name | Delete/cancel with linked-data check | Search, type, sort, pagination | N/A | Active/inactive if exposed | Cost, yield, loss, margin, target food cost | Automated partial pass; UAT pending | Existing tests cover hidden ids, duplicate-name, positive row validation. |
| Recipes | Recipe to indent | Create ingredient request from recipe | Indent created with items | N/A | Cancel if allowed | N/A | N/A | Recipe request to submitted indent | No stock change until fulfilment | Pending UAT | Confirm sub-recipes expand correctly. |
| Indents | Indent CRUD/status | Create `QA Indent` with department and one positive item | Detail and table rows load | Edit when allowed | Cancel/delete when allowed | MRN/search, status, department, requester, sort, pagination | Print/PDF/export | Submitted, approved, processing, completed, cancelled | Fulfilment reduces stock | Automated partial pass; UAT pending | Existing tests cover empty indent rejection and issue transaction boundary. |
| Indents | Fulfilment | N/A | Issue form loads | Enter partial/full issue quantities | Cancel issue | N/A | N/A | Approved to processing/completed | Creates ISSUE transaction, blocks over-issue | Pending UAT | Browser-test `Issue Selected` with QA stock. |
| Order Planner | Consolidation | Generate from approved indents | Preview groups by supplier | Quantity overrides/exclusions | Cancel preview | Supplier/item eligibility | Create POs | Approved indent to PO link | Planned quantities only, no stock mutation | Pending UAT | Add more tests if duplicate PO lines are reproduced. |
| Purchase Orders | PO CRUD | Create `QA PO` with supplier/order date/line | Detail opens | Edit line and notes | Cancel/delete if supported | Search, status, supplier, dates, table/cards | CSV export, print/download | Draft to sent to received/cancelled if supported | Pending/received totals and item last purchase price | Automated partial pass; UAT pending | PR #853 fixes detail receive drawer behavior and PO line price history updates. |
| Purchase Orders | Supplier search | Select supplier by partial/case-insensitive name | N/A | Preserve supplier on edit | N/A | Full and partial name suggestions | N/A | N/A | Supplier drives PO/vendor price hints | Automated partial pass; UAT pending | Existing form resolves exact, id, and unique partial active supplier. |
| Receiving/GRNs | PO receiving | Receive partial and full quantities | GRN detail/list load | N/A | Cancel receive | GRN list filters | GRN export/download | PO partial/full received | Creates GRN, updates stock and PO progress | Automated partial pass; UAT pending | Existing tests cover over-receipt rejection and stock preservation. |
| Receiving/GRNs | Ad-hoc receiving | Create ad-hoc GRN if business-approved | Detail/list load | N/A | Cancel | Filters/search | Export | GRN received | Updates stock without PO | Pending owner confirmation | Confirm ad-hoc receiving is intended before go-live. |
| Stock Movements | Receive stock | Item and quantity required; date defaults today | Transaction appears | N/A | N/A | Search/type/date range and clear dates | Bulk upload | RECEIVING | Increases item stock | Automated partial pass; UAT pending | Verify in-app validation messages. |
| Stock Movements | Adjust stock | Item, quantity change, reason required | Transaction appears | N/A | N/A | Search/type/date range | Bulk upload | ADJUSTMENT | Positive/negative adjustment, prevent unintended negative stock | Automated partial pass; UAT pending | Existing tests cover missing reason errors; PR #853 adds bulk negative-stock rollback coverage. |
| Stock Movements | Wastage | Item, quantity, category required; photo optional | Transaction appears | N/A | N/A | Search/type/date range | N/A | WASTAGE | Reduces stock | Automated partial pass; UAT pending | Verify negative stock prevention. |
| Stock Movements | Transfer | Item, quantity, from and to departments required | Transaction appears | N/A | N/A | Search/type/date range | N/A | TRANSFER | Department movement; item total policy must be confirmed | Pending UAT | Source and destination cannot match. |
| Stock Takes | Start/count/review | Start `QA Stock Take` | Count page and review page load | Enter counts | Cannot edit or discard after completion unless intended | List/status filters | N/A | Draft, in progress, completed | Variance creates adjustment transactions | Automated partial pass; UAT pending | PR #853 blocks direct discard of completed stock takes; confirm all-department behavior. |
| Vendor Prices | Price comparison | CRUD if implemented | List/comparison loads | Edit if implemented | Delete if implemented | Search/filter | Export if implemented | N/A | Used by PO/order planner if enabled | Pending UAT | Current route appears list/comparison focused. |
| Global UX | Navigation/search/notifications/profile | N/A | Menus, notifications, profile load | Profile/password pages | Logout/session handling | Global search if present | N/A | N/A | N/A | Smoke automated pass; UAT pending | Verify no HTML entities in toasts and focus is sane. |
| Imports/exports | Bulk uploads/downloads | Upload valid QA CSV | Error rows visible | N/A | Cancel upload | N/A | Download filtered CSVs | N/A | Depends on imported data | Pending UAT | Keep QA data identifiable and cleanable. |

## P0 Browser UAT Checklist

1. Create item -> edit item -> receive stock -> adjust stock -> transaction appears.
2. Create supplier -> link to item/vendor price if supported -> create PO.
3. Create recipe -> request ingredients -> indent appears.
4. Approve indent -> order planner consolidation -> create PO.
5. Receive PO -> GRN created -> item stock updated -> PO status/progress updated.
6. Create stock take -> enter count -> review variance -> complete -> stock adjusted.
7. Record wastage -> stock reduces -> wastage transaction appears.
8. Transfer stock -> source/destination department movement appears and same-department transfer is blocked.

## Current Evidence

- P0 regression red checks were observed for PO detail receive drawer wiring, PO item price history updates, bulk negative-stock rollback, and completed stock-take discard protection.
- P0 focused Python suite after fixes: `74 passed`.
- P0 focused Jest suite after fixing stale column-filter import: `7 passed` suites, `18 passed, 2 skipped`.
- P0 authenticated route smoke after fixes: `80 passed, 11 skipped`.
- P1 accessibility/smoke suite after fixes: `99 passed, 11 skipped`.
- `manage.py check`: no issues on P0 and P1 branches.
