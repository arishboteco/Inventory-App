# Example Fix Prompt — Phase A (3 Fixes)

This is a real example of a well-structured fix prompt generated for a Django inventory app. Use it as a reference when generating new prompts.

---

## Starting State

- App: Django F&B inventory app called **Inventory Pro**
- Live URL: `https://inventory-app-kguo.onrender.com/`
- Login: `admin` / `admin123!`
- Three bugs are blocking the entire procurement pipeline — no PO can be created by any path

## Target State

After all three fixes:

1. Manual PO creation saves a PO and returns `{"ok": true}`
2. Consolidation Planner → Confirm & Create → redirects to `/purchase-orders/` with new POs listed
3. **New Purchase Order** (drawer) opens, saves, and returns `{"ok": true}` when valid

## Forbidden Actions

- Do NOT run migrations without stopping to show the migration file content
- Do NOT change any model field not directly involved in the three bugs
- Do NOT modify any file that isn't referenced in the fix steps below
- Do NOT change anything in the Indent, GRN, Stock Movements, or Recipe modules
- Do NOT refactor or rename anything

## Stop Conditions — MANDATORY

Stop immediately and report if:

- A migration is required and you are unsure if it is safe on production data
- The `purchase_order_items` table schema is different from what the bug description says
- The consolidation view creates POs via a Celery task instead of inline
- Any fix causes a test suite to fail

## Fix 1 of 3 — Consolidation → PO creation returns 500

### Context

The manual PO create view was fixed but the consolidation view was not. It still passes an invalid `po_number` kwarg.

### Steps

1. Find the consolidation view:

```bash
grep -rn "consolidate" --include="*.py" | grep -i "def \|view\|class "
```

2. Remove the `po_number` kwarg from `PurchaseOrder.objects.create()`.

3. Also apply the `line_total` fix to the item creation loop.

### Checkpoint Output

```
✅ Fix 1 applied: Removed po_number from consolidation view at [file]:[line]
```

## Fix 2 of 3 — line_total NOT NULL constraint

### Context

After removing `po_number`, saving a PO fails with `null value in column 'line_total'`.

### Steps

**Part A — Model safety net:**

```python
def save(self, *args, **kwargs):
    if self.quantity_ordered is not None and self.unit_price is not None:
        self.line_total = self.quantity_ordered * self.unit_price
    super().save(*args, **kwargs)
```

**Part B — View explicit computation:**
Set `line_total = quantity * unit_price` before saving each PO item.

### Checkpoint Output

```
✅ Fix 2 applied: line_total auto-computed in model save() and view
```

## Fix 3 of 3 — PO create drawer does not save (JS / JSON)

### Steps

1. Confirm partial URL and `data-modal-form` wiring: `purchase_order_create_partial`
2. Ensure POST returns JSON for `X-Requested-With: XMLHttpRequest` and `partial=1`
3. If validation fails, return 400 with structured `errors` for the modal list

### Checkpoint Output

```
✅ Fix 3 applied: PO create drawer saves and surfaces field errors in the modal
```

## Final Verification

```
STEP 1 — Create Indent → Submit → Appears with status Pending ✅
STEP 2 — Approve Indent → Status changes to Approved ✅
STEP 3 — Consolidation Planner → Create POs → Redirects to PO list ✅
STEP 4 — Open PO → Line items have correct quantities and totals ✅
STEP 5 — Create GRN → Select PO → Fill received quantities → Save ✅
STEP 6 — Fulfill Indent → Status changes to Completed ✅
STEP 7 — Check stock → Level increased ✅

If all pass:
✅ PHASE A COMPLETE — Ready for Phase B.
```
