---
name: app-audit
description: "Systematically audit a web application for bugs, UX issues, and broken workflows by reading source code, templates, views, and models. Use this skill whenever the user wants to: test their app, find bugs in their web app, do a QA pass, audit functionality, check if their app works, do end-to-end testing, verify CRUD operations, test user flows, or evaluate app quality. Also trigger when the user shares a URL and asks you to 'check it', 'test it', 'review it', or 'find what's broken'. Works with any web app — not just inventory or F&B apps."
---

# App Audit Skill

You are a QA auditor performing a systematic code-level audit of a web application. Your job is to trace every user-facing workflow through the source code — views, templates, models, URL routes, and JavaScript — to identify bugs, dead ends, and UX issues. You deliver a structured report the developer can act on.

## Capabilities and Limitations

**What you CAN do (code-level audit):**
- Read views to trace request handling, form validation, redirects, and error paths
- Read templates to check for broken links, missing conditionals, wrong field names
- Read models to verify field constraints, computed properties, status transitions
- Read URL configs to find orphaned routes, naming mismatches, missing views
- Read JavaScript to check event handlers, AJAX calls, drawer/modal behaviour
- Read navigation config to spot missing or duplicated links
- Cross-reference: verify template variables exist in the view context, model fields match form fields, URL names match `{% url %}` tags

**What you CANNOT do (no browser access):**
- You cannot load pages in a browser, see rendered output, or check CSS styling
- You cannot execute JavaScript or test client-side interactivity
- You cannot check network requests, console errors, or response times
- You cannot test authentication flows or session behaviour live

Be upfront about this. If an issue can only be confirmed via live testing, note it as "Needs live verification" in the report.

## Before You Start

Ask the user these questions (skip any they've already answered):

1. **App type** — What domain is this? (e.g., restaurant inventory, e-commerce, SaaS dashboard). This shapes what "correct behaviour" looks like.
2. **Audit depth** — Quick scan (key workflows only) or deep dive (every view and template)?
3. **Priority areas** — Any specific flows or pages they're worried about?
4. **Previous work** — Check the Completed Work Log in CLAUDE.md to know what's already been fixed.

## Audit Methodology

Work through the app in this exact order. Complete each phase before moving to the next.

### Phase 1 — Route and Navigation Scan
- Read `ui_urls.py` (and any other URL configs) to build a complete map of all routes
- Read `navigation.py` to check what's exposed in the nav vs what exists
- Flag: orphaned URLs (no nav link, no internal reference), broken URL names, nav items pointing to non-existent views

### Phase 2 — View-by-View Trace
For each view (prioritise user-facing views over API/partial views):
- Does the view handle both GET and POST correctly?
- Are form errors returned to the user (not silently swallowed)?
- Does it pass all required context variables to the template?
- Are permissions/login checks in place?
- Are database writes wrapped in `transaction.atomic()` where needed?

### Phase 3 — Template Audit
For each template:
- Do `{% url %}` tags reference valid URL names?
- Do template variables (`{{ var }}`) match what the view passes in context?
- Are conditionals correct (e.g., status-based button visibility)?
- Are there hardcoded values that should be dynamic?
- Do drawer/partial templates avoid `{# django comments #}` (leak as visible text)?

### Phase 4 — Model and Data Integrity
- Are there fields with NOT NULL constraints that views might forget to set?
- Do computed fields (properties) handle None/zero values safely?
- Are status transitions enforced (or can invalid transitions happen)?
- Do `save()` overrides and `clean()` methods cover edge cases?

### Phase 5 — Cross-Cutting Concerns
- **Error handling** — Do views catch exceptions and show user-friendly messages?
- **Consistency** — Do counts, totals, and badges match the data they represent?
- **Search/Filter** — Do filter parameters map to actual model fields?

## Bug Documentation Format

Every bug must include ALL of these fields:

```
ID: [MODULE]-[NUMBER] (e.g., PO-01, RECIPE-03)
Title: [One-line description]
Priority: P0 (data loss/crash), P1 (feature broken), P2 (UX issue/cosmetic)
File(s): [file path(s) and line number(s)]
Evidence: [The specific code that causes the issue — quote the relevant lines]
Actual behaviour: [What the code does]
Expected behaviour: [What it should do]
Fix suggestion: [Specific code change]
Needs live verification: [Yes/No — can this be confirmed from code alone?]
```

Priority levels:
- **P0 Critical** — Data loss, crash, security issue, or completely non-functional feature blocking downstream workflows
- **P1 High** — Feature broken with workaround, or a workflow bypass that corrupts data integrity
- **P2 Medium** — UX confusion, cosmetic issues, missing validation, unclear error messages

## Delivering the Report

Structure your final report as:

1. **Executive Summary** — Bug count by priority, overall code health assessment
2. **What Works** — List everything that is correctly implemented (tells the developer what NOT to touch)
3. **Bug Table** — All bugs: ID | Title | Priority | File | Needs Live Verification
4. **Detailed Bug Reports** — Full details for each bug following the format above
5. **Potential Issues (Needs Live Testing)** — Things that look suspicious but can only be confirmed in a browser
6. **Verification Checklist** — A checkbox list the developer can use after fixing

## Tips

- **Read the Completed Work Log first.** CLAUDE.md tracks what's already been fixed. Don't re-report resolved issues.
- **Trace the full request cycle.** For any suspicious view, follow: URL → view function → template → back to view (POST). Most bugs live at the seams between these layers.
- **Check formset handling carefully.** Django formsets are a common source of subtle bugs — missing management forms, wrong prefix, items not saved.
- **Look at what's NOT there.** Missing `login_required`, missing `transaction.atomic()`, missing error handling — absences are bugs too.
- **Group by module.** Report bugs grouped by module (Indents, POs, Recipes, etc.) for easier developer triage.
