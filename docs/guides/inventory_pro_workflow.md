# Inventory Pro Workflow Handbook

The flow below captures how planners should move through Inventory Pro to raise, source, receive, and fulfil requests. Each stage maps to the updated UI heroes, toast notifications, and guidance banners implemented during the CDL work.

```mermaid
flowchart LR
    A[Department raises Indent] --> B[Indent Review & Approval]
    B --> C{Need PO?}
    C -- Yes --> D[Consolidate Approved Indents]
    D --> E[Generate Purchase Orders]
    C -- No --> F[Issue From Stock]
    E --> G[Receive Goods (GRN)]
    G --> H[Fulfil Indent]
    H --> I[Update Stock Movements]
    F --> I
```

## Stage Details

1. **Raise Indent** (`/indents/` drawer)
   - Users submit requisitions via the New Indent drawer. Successful creation shows a toast and redirects to the Indent detail hero with the next-step banner.
   - Key data: department, required date, line items.

2. **Review & Approval** (`/indents/<id>/` detail)
   - Approvers use the hero status badge to move from *Submitted* to *Approved*.
   - The list hero now surfaces the count of approved indents waiting for consolidation.

3. **Consolidate Approved Indents** (`/indents/consolidate/preview/`)
   - Banner indicates how many POs can be created. Posting the form emits a toast confirming new purchase orders.
   - If no eligible items remain, an info toast explains why.

4. **Generate Purchase Orders** (`/purchase-orders/`)
   - Quick create drawer and list hero highlight outstanding receipts (orders in `ORDERED`/`PARTIAL`).
   - Detail hero chips show supplier, order dates, and provide CTA for receiving goods.

5. **Receive Goods (GRN)** (`/purchase-orders/<id>/receive/` or `/grns/`)
   - GRN creation fires a toast and redirects to the GRN detail hero, which records supplier and PO data.
   - GRN list hero summarises supplier/date filters.

6. **Fulfil Indent** (`/indents/<id>/issue/`)
   - Next-step banner explains whether to issue goods or close the indent; success toast returns to the detail view.

7. **Update Stock Movements** (`/stock-movements/`)
   - Hero meta shows active form, total records, and pending PO receipts. Each modal submission (receive, adjust, wastage, quick move) now triggers toast feedback.

### Verification Checklist
- Creating an indent surfaces the toast and “Next step” banner.
- Consolidation produces purchase orders and corresponding toast.
- Purchase order hero shows supplier/date meta and pending receipt banner on the list.
- GRN creation routes to detail with status badge and toast.
- Fulfilment updates the indent with a completion toast.
- Stock adjustments, including quick moves and bulk upload, emit toast notifications and reopen modals when validation fails.

When following the flowchart, every stage above is now backed by on-screen guidance and toast confirmation, matching the implemented logic.
