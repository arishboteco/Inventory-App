# Common Bug Patterns Found in Web App Audits

This reference captures recurring patterns from real audits. When auditing, watch for these — they show up across many Django/HTMX/Bootstrap apps.

## 1. Drawer/Modal Forms That Navigate Instead of Submitting via AJAX

**Pattern:** A form inside a slide-in drawer has `action="/some/partial/"` but no HTMX/fetch handler. Clicking submit navigates the full page to the partial URL, rendering raw unstyled HTML.

**How to spot it:** Click any submit button inside a drawer. If the page navigates away from the current URL to a `/partial/` or `/create/` endpoint, this bug is present.

**Root cause:** The form relies on `hx-post` or a JS `fetch()` handler that was either never added or is not attaching to the DOM element (e.g., element rendered after the handler was registered).

**Fix pattern:** Either add HTMX attributes to the form or replace the submit button with a `type="button"` + `fetch()` handler.

## 2. Buttons That Don't Respond to Clicks

**Pattern:** A button with `data-modal-url` or `data-action` attributes does nothing when clicked.

**How to spot it:** Check browser console for JS errors on page load. The delegated click handler may not be initialized.

**Common causes:**

- Event listener uses `querySelectorAll` on load, misses dynamically added buttons
- JS error earlier in the file prevents the handler from registering
- Button is inside a `<form>` tag that intercepts the click

**Fix pattern:** Use event delegation on `document` instead of attaching to individual elements.

## 3. Django Template Comments Rendered as Visible Text

**Pattern:** `{# some comment #}` appears as visible text on the page.

**How to spot it:** Search the DOM for `{#` or look for developer-facing text on the rendered page.

**Root cause:** The comment is in a template that's `{% include %}`d as raw text, or in a block that's not processed as Django template syntax.

**Fix:** Delete the comment or convert to HTML `<!-- comment -->`.

## 4. Status-Blind Action Buttons

**Pattern:** A detail view or drawer shows the same set of action buttons (Approve, Process, Complete, Cancel) regardless of the entity's current status. Users can skip required workflow steps.

**How to spot it:** Open the same entity at different statuses and compare the available buttons. They should change.

**Fix pattern:** Wrap buttons in `{% if entity.status == 'X' %}` conditionals.

## 5. Model Field Mismatch After Migration

**Pattern:** A view tries to create/update a model with a keyword argument that doesn't exist on the model (field was renamed or removed in a migration, but the view wasn't updated).

**How to spot it:** Submit a form and check for `TypeError: Model() got unexpected keyword arguments` in the response.

**Fix:** Check the model definition, find the correct field name, update the view.

## 6. NOT NULL Constraint Violations on Computed Fields

**Pattern:** A computed field (like `line_total = qty × price`) has a NOT NULL constraint in the database, but the view doesn't compute it before saving.

**How to spot it:** Submit a form that creates a record with related items. Check for `IntegrityError: null value in column 'X' violates not-null constraint`.

**Fix:** Compute the field before save, both in the view and as a safety net in the model's `save()` method.

## 7. Chart/Visualization Date Formatting

**Pattern:** Charts show millisecond-precision timestamps (e.g., "23:59:59.9995") instead of readable dates.

**How to spot it:** Look at any chart's x-axis.

**Root cause:** Dates passed as datetime objects instead of date strings; chart library defaults to time-of-day formatting.

**Fix:** Pass dates as `'%Y-%m-%d'` strings, set `tickformat: '%b %d, %Y'` on the axis.

## 8. Duplicate Reference Data With No Uniqueness Constraint

**Pattern:** The settings/admin page allows creating "Admin" and "Administration" as separate entities with no dedup.

**How to spot it:** Browse any reference data list (departments, categories, units) and look for near-duplicates.

**Fix:** Case-insensitive uniqueness check in the model's `save()` or form's `clean()` method.
