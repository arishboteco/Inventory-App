---
name: production-readiness-checker
description: "Evaluate a web application's readiness for production use and generate a phased roadmap to get there. Use this skill when the user asks: 'is my app ready for production', 'what do I need before launch', 'production readiness review', 'what's missing from my app', 'how do I get this production-ready', 'launch checklist', or wants to assess the gap between their current app and a production-quality product. Also trigger when the user has finished fixing bugs and asks 'what's next' or 'what should I work on now'. Works for any web app in any domain."
---

# Production Readiness Checker

You evaluate a web application against production readiness criteria and produce a phased roadmap from "current state" to "ready to serve real users." The output is not a generic checklist — it's specific to the app's domain, scale, and user base.

## Why a Phased Approach

Throwing a 40-item checklist at a developer is paralysing. They don't know what to do first, so they do nothing — or worse, they spend a week on something cosmetic while a critical workflow is broken. The phased approach solves this by grouping work into clear stages where each stage delivers measurable value and gates the next.

## Step 1: Understand the Context

Before evaluating, establish:

1. **What does this app do?** (domain, core workflow)
2. **Who uses it?** (internal team of 5? public SaaS? restaurant kitchen staff?)
3. **What's the scale?** (10 users/day? 10,000?)
4. **What's already been done?** Check the **Completed Work Log** section in CLAUDE.md — it tracks all phases completed so far. Don't re-evaluate fixed issues.
5. **What's the deployment target?** (already hosted? needs CI/CD? compliance requirements?)

The answers shape every recommendation. A 5-person internal tool doesn't need GDPR compliance flows. A public SaaS doesn't need kitchen station assignments.

## Step 2: Evaluate Against Five Dimensions

### Dimension 1 — Core Workflow Integrity
The most important dimension. Can a user complete the primary workflow end-to-end without errors?

Walk the happy path. If the app is an inventory system, that's: create an order → receive goods → update stock. If it's an e-commerce app: browse → add to cart → checkout → confirm.

Questions to answer:
- Does the happy path complete without errors?
- Does each step's output correctly feed into the next step?
- Are there dead ends where the user gets stuck?
- Are there steps that silently fail (no error, but no effect either)?

If the core workflow is broken, nothing else matters. This is always Phase A.

### Dimension 2 — Data Integrity & Consistency
Can the app be trusted with real data?

- Do totals, counts, and status badges match the actual data?
- Are there duplicate records that shouldn't exist? (e.g., "Admin" + "Administration")
- Are calculations correct? (costs, percentages, aggregations)
- Can required fields be left empty?
- Is there validation on inputs that affect downstream data?

### Dimension 3 — UX Clarity
Can a new user figure out what to do without training?

This is where you look for:
- **Redundant paths** — Two ways to do the same thing with no guidance on which to use
- **Confusing distinctions** — Two similar actions with unclear differences (e.g., "Adjust Stock" vs "Record Wastage")
- **Missing context** — Pages that show data without explaining what it means or what to do with it
- **Name mismatches** — Nav says one thing, page title says another
- **Status overload** — Too many status steps for a simple workflow

Document each issue in a table:

| # | Issue | User Impact | Fix |
|---|-------|-------------|-----|

### Dimension 4 — Domain Feature Completeness
Does the app have the features its domain requires?

This is domain-specific. For a restaurant inventory app, you'd check: sub-recipes, food cost %, allergen tracking, stock-take workflow, waste reason codes. For an e-commerce app: order tracking, refund flow, inventory sync, email notifications.

Research what's standard for the domain. List missing features by impact:
- **Critical** — App is fundamentally incomplete without this
- **High** — Users will hit this gap within the first week
- **Medium** — Nice to have, will be requested eventually

### Dimension 5 — Operational Readiness
Can the app run reliably in production?

- **Error handling** — What does the user see when something goes wrong?
- **Performance** — Are there slow pages or queries?
- **Security** — Authentication, authorization, CSRF, input sanitisation
- **Backup & recovery** — Is data backed up? Can you restore?
- **Monitoring** — Will you know when something breaks?
- **Deployment** — Is there a CI/CD pipeline? Can you roll back?

## Step 3: Build the Phased Roadmap

Group all findings into phases following this structure:

### Phase A — Unblock Core Workflow
Fix anything that prevents the primary happy path from completing. This is always the highest priority and should take no more than a few days. Gate: the happy path works end-to-end.

### Phase B — Fix Known Bugs
All remaining bugs from the audit, ordered P0 → P1 → P2. Gate: all bugs resolved, no regressions.

### Phase C — Remove UX Confusion
Address redundant paths, confusing distinctions, missing guidance. These are typically low-effort, high-impact template and copy changes. Gate: a new user can navigate the core workflow without asking questions.

### Phase D — Add Missing Features
Domain-specific features the app needs. Order by: blocking features first, then high-impact, then nice-to-have. Gate: feature checklist complete, tested.

### Phase E — Data Quality & Reporting
Reports, analytics, data cleanup, and data presentation improvements. Gate: key metrics are accurate and accessible.

### Phase F — Scale & Compliance
Performance, security, multi-user/multi-location support, compliance requirements. Gate: app can handle target load with proper access controls.

## Roadmap Format

For each phase, produce a table:

| Step | Task | Bug/Feature ID | Effort Estimate |
|------|------|---------------|-----------------|

Include:
- **A gate at the end of each phase** — what must be true before moving to the next phase
- **A recommended order** within each phase — what to tackle first and why
- **Effort estimates** — rough time ranges (30 min, 4 hrs, 1-2 days, 1 week)
- **Risk flags** — any item that might take longer than estimated or has dependencies

## Output

Save the roadmap as a markdown file: `[app-name]-production-roadmap.md`

The roadmap should be readable by a non-technical stakeholder (for phases and priorities) while also being actionable by a developer (for specific tasks and effort estimates). The audience is someone who needs to plan a sprint or allocate time — give them what they need to make decisions.

## After the Roadmap

Offer to generate Claude Code fix prompts for each phase using the fix-prompt-generator skill. This turns the roadmap from a plan into executable instructions.
