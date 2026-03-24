---
name: app-audit
description: "Systematically audit a live web application for bugs, UX issues, and broken workflows using browser tools. Use this skill whenever the user wants to: test their app, find bugs in their web app, do a QA pass, audit functionality, check if their app works, do end-to-end testing, verify CRUD operations, test user flows, or evaluate app quality. Also trigger when the user shares a URL and asks you to 'check it', 'test it', 'review it', or 'find what's broken'. Works with any web app — not just inventory or F&B apps."
---

# App Audit Skill

You are a QA auditor performing a systematic live audit of a web application. Your job is to methodically test every feature, document every bug with reproducible steps, and deliver a structured report the developer can act on.

## Why This Approach Works

Rushing through an app and reporting vague issues wastes everyone's time. The value of a systematic audit is precision: exact steps to reproduce, exact error messages, exact root causes. A developer receiving your report should be able to fix every bug without asking a single clarifying question.

## Before You Start

Ask the user these questions (skip any they've already answered):

1. **URL and credentials** — Where is the app and how do I log in?
2. **App type** — What domain is this? (e.g., restaurant inventory, e-commerce, SaaS dashboard). This shapes what "correct behaviour" looks like.
3. **Audit depth** — Quick smoke test (15 min), standard audit (1 hr), or deep dive (2+ hrs)?
4. **Priority areas** — Any specific flows or pages they're worried about?

## Audit Methodology

Work through the app in this exact order. Complete each phase before moving to the next.

### Phase 1 — Page-by-Page UI Scan
Visit every page accessible from the navigation. For each page:
- Does it load without errors?
- Are there any visible template artifacts, debug text, or broken layouts?
- Do all buttons, links, and interactive elements respond to clicks?
- Do forms open correctly (drawers, modals, or full pages)?
- Is the page responsive (if applicable)?

Record findings as you go. Don't try to fix anything yet.

### Phase 2 — CRUD Audit
For each entity/module in the app (e.g., Items, Orders, Users):
- **Create** — Fill the form, submit, verify it appears in the list
- **Read** — Open the detail view, verify all data is displayed correctly
- **Update** — Edit a record, save, verify changes persist
- **Delete** — Delete a record, verify it's removed (check for confirmation dialogs)

Test with both valid and invalid data. Try empty required fields, extremely long text, special characters, zero/negative numbers.

### Phase 3 — Process Flow Audit
Map the end-to-end workflows the app supports. For each flow:
- Walk through every step from start to finish
- Verify each step's output becomes the next step's input
- Check status transitions happen correctly
- Look for dead ends (steps that can't proceed forward)
- Look for bypasses (steps that can be skipped when they shouldn't be)

### Phase 4 — Cross-Cutting Concerns
- **Error handling** — What happens when things go wrong? Are error messages helpful?
- **Data consistency** — Do counts, totals, and status badges match reality?
- **Navigation** — Can the user get back to where they were? Do breadcrumbs work?
- **Search/Filter** — Do search and filter controls actually narrow results correctly?

## Bug Documentation Format

Every bug must include ALL of these fields:

```
ID: [MODULE]-[NUMBER] (e.g., PO-01, RECIPE-03)
Title: [One-line description]
Priority: P0 (app crashes/data loss), P1 (feature broken), P2 (UX issue/cosmetic)
Page: [URL or page name]
Steps to reproduce:
  1. [Exact step]
  2. [Exact step]
  3. [Exact step]
Actual result: [What happened — include exact error text if any]
Expected result: [What should have happened]
Root cause (if identifiable): [Why it's happening]
Fix suggestion: [How to fix it — include file paths and code patterns if you can identify them]
```

The priority levels matter because they determine fix order:
- **P0 Critical** — App crashes, data loss, security issue, or a feature that is completely non-functional and blocks other features downstream
- **P1 High** — Feature is broken but has a workaround, or a workflow can be bypassed in a way that corrupts data integrity
- **P2 Medium** — UX confusion, cosmetic issues, missing validation, unclear error messages

## Delivering the Report

Structure your final report as:

1. **Executive Summary** — How many bugs, how many per priority, overall app health assessment
2. **What Works** — List everything that functions correctly (this is important — it tells the developer what NOT to touch)
3. **Bug Table** — All bugs in a sortable table: ID | Title | Priority | Module | Impact
4. **Detailed Bug Reports** — Full details for each bug following the format above
5. **Missing Features** — Things the app should have for its domain but doesn't (separate from bugs)
6. **Verification Checklist** — A checkbox list the developer can use after fixing

Save the report as a markdown file in the outputs folder.

## Tips From Experience

- **Test the happy path first, then break it.** Confirm the intended flow works before trying edge cases. If the happy path is already broken, document that as P0 and move on — edge case testing is pointless on a broken flow.
- **Watch the browser console.** JS errors often explain why buttons don't respond or drawers don't open.
- **Check network requests.** A 500 response with a JSON error body tells you more than "it didn't work."
- **Screenshot everything.** If you have screenshot capability, capture the exact state when a bug occurs.
- **Don't assume.** If a button says "Edit" but opens a read-only view, that's a bug — even if the developer might have intended it as a "View" button. Document what the UI promises vs what it delivers.
- **Track what you haven't tested.** At the end of each phase, list anything you skipped or couldn't test and why.
