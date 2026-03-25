# Domain-Specific Feature Checklists

When evaluating production readiness, use the relevant domain checklist below to identify missing features. These are based on industry standards — not every app needs every item, but missing critical ones should be flagged.

Items marked with [DONE] are already implemented in Inventory Pro (see CLAUDE.md Completed Work Log for details).

## Restaurant / F&B Inventory

### Critical (app is incomplete without these)
- [DONE] Sub-recipes / semi-processed items (a recipe using another recipe as an ingredient)
- [DONE] Food Cost % (total ingredient cost / selling price x 100) — the #1 metric
- [DONE] Physical stock-take workflow (count vs system, variance tracking, auto-adjust)
- [DONE] Full procurement pipeline: Indent → PO → GRN → Stock update

### High (users will notice within first week)
- [DONE] Stock transfers between departments (Kitchen ↔ Bar ↔ Pastry)
- [DONE] Low-stock alerts with auto-reorder action
- [DONE] Ad-hoc receiving (goods without a PO — emergency purchases)
- Allergen tracking on items, auto-display on recipes
- [DONE] Wastage reason codes (Spoiled / Over-prep / Dropped / Expired)

### Medium (will be requested eventually)
- Batch/lot tracking with expiry dates
- [DONE] Consumption tracking — auto-deduct stock when a recipe is produced
- Food cost trend reports over time
- Recipe profitability ranking
- Prep instructions and station assignment on recipes
- Supplier performance scoring (on-time %, quality issues)

### Scale features
- Multi-outlet / location support
- Role-based access (kitchen staff vs manager vs admin)
- Mobile-optimised views for kitchen station use
- Scheduled reports by email (daily wastage, weekly food cost)
- Integration with POS for auto-consumption

## E-Commerce

### Critical
- Product catalog with categories, variants, and images
- Shopping cart with session persistence
- Checkout flow with order confirmation
- Payment processing integration
- Order status tracking (Placed → Processing → Shipped → Delivered)

### High
- Inventory sync (stock count decrements on order)
- Email notifications (order confirmation, shipping update)
- Refund / return workflow
- Search with filters (price, category, rating)
- User account with order history

### Medium
- Wishlist / save for later
- Product reviews and ratings
- Discount codes / promotions
- Abandoned cart recovery emails
- Related products / recommendations

## SaaS Dashboard

### Critical
- User authentication and session management
- Core data visualisation (charts, tables, KPIs)
- Data refresh / real-time updates
- Export capability (CSV, PDF)

### High
- Role-based access control (admin, editor, viewer)
- Filtering and date range selection
- Alerts and notifications on threshold breaches
- API access for integrations

### Medium
- Custom dashboard layouts
- Scheduled report delivery
- Audit log of user actions
- White-labelling / branding options

## Internal Tool

### Critical
- Authentication (SSO preferred for internal tools)
- Core CRUD for the primary entities
- Basic search and filtering

### High
- Audit trail (who changed what, when)
- Bulk operations (import/export)
- Clear error messages and validation

### Medium
- Activity feed / changelog
- Keyboard shortcuts for power users
- Dark mode (surprisingly common request for internal tools)
