---
name: fix-prompt-generator
description: "Generate structured Claude Code fix prompts from a bug list or audit report. Use this skill whenever the user has a list of bugs, issues, or changes and wants to create a prompt they can paste into Claude Code to get them fixed. Also trigger when the user says 'generate a fix prompt', 'create a prompt for Claude Code', 'write instructions for fixing these', 'make this into an agentic prompt', or has an audit/review they want turned into actionable Claude Code instructions. Works for any codebase — not just Django or web apps."
---

# Fix Prompt Generator

You generate structured prompts that a developer can paste into Claude Code to fix a batch of bugs or implement a batch of changes. The prompts follow a specific format designed for agentic execution — meaning Claude Code can run them autonomously with minimal human intervention while still stopping when it encounters something unexpected.

## Why This Format Matters

A plain bug list ("fix the login page, fix the search, fix the chart") leads to unpredictable results. Claude Code might over-engineer, break unrelated features, or silently skip something it couldn't figure out. The structured format below prevents all of this by giving the agent clear boundaries, a defined starting point, and explicit conditions under which it must stop and ask for help instead of guessing.

## The Prompt Template

Every fix prompt you generate must include these six sections in this order:

### 1. Starting State

Tell the agent exactly what's already been done, what's working, and what the current status of the codebase is. This prevents the agent from re-investigating things you already know.

```markdown
## Starting State

- App: [framework, language, name]
- What's working: [list modules/features that are confirmed functional]
- What's broken: [brief summary of what this prompt will fix]
- Previous fixes applied: [if this is part of a phased plan]
```

### 2. Target State

Describe what "done" looks like in concrete, testable terms. Not "fix the bugs" — instead, describe the specific behaviours that should be true after all fixes are applied.

```markdown
## Target State

After all fixes:

1. [Specific testable behaviour]
2. [Specific testable behaviour]
3. [Specific testable behaviour]
```

### 3. Forbidden Actions

Explicitly list what the agent must NOT do. This is critical because Claude Opus especially tends to over-engineer — it will refactor, rename, reorganise, and "improve" things that aren't part of the fix. Without this section, a 3-bug fix prompt can turn into a 50-file refactor.

```markdown
## Forbidden Actions

- Do NOT change any file not directly referenced in the fixes below
- Do NOT refactor, rename, or reorganise anything
- Do NOT run migrations without showing the migration file first
- Do NOT modify [list specific modules that are working and must not be touched]
- Only make changes directly requested in this prompt
```

### 4. Stop Conditions (MANDATORY)

These are the hard stops — situations where the agent must pause, report what it found, and wait for the human before continuing. Without stop conditions, the agent will guess and often guess wrong.

Think of stop conditions as "if reality doesn't match my assumptions" guards:

```markdown
## Stop Conditions — MANDATORY

Stop immediately and report to the user if:

- [A model/schema is different than the fix assumes]
- [A migration is needed and you're unsure if it's safe on production data]
- [A file or function mentioned in the fix doesn't exist]
- [The fix causes a test to fail]
- [Any specific edge case where guessing would be dangerous]
```

Good stop conditions are specific and actionable. "Stop if something goes wrong" is useless. "Stop if the `PurchaseOrderItem` table doesn't have a `line_total` column" is useful.

### 5. The Fixes

Each fix gets its own numbered section with:

- **Context** — Why this bug exists and what the user sees
- **Steps** — Exact commands to find the relevant code, followed by the specific change to make. Always start with a `grep` or file search so the agent locates the right file even if the codebase structure is slightly different than assumed.
- **Checkpoint output** — A `✅` line the agent prints after completing the fix, confirming what was changed and where

```markdown
## Fix 1 of N — [BUG-ID] · [One-line title] (Priority)

### Context

[Why this bug exists, what the user sees, what the root cause is]

### Steps

**Step 1 — Find the relevant code:**
\`\`\`bash
grep -rn "[search term]" --include="\*.py"
\`\`\`

**Step 2 — Make the change:**
[Specific code change with before/after]

### Checkpoint Output

\`\`\`
✅ [BUG-ID] fixed: [what was changed] at [file]:[line]
\`\`\`
```

### 6. Final Verification

A complete end-to-end test the agent runs after all fixes, to confirm nothing is broken:

```markdown
## Final Verification

After all fixes, test:
□ [Step 1 — specific action → expected result]
□ [Step 2 — specific action → expected result]
□ [Step N]

If all pass:
\`\`\`
✅ [PHASE/BATCH NAME] COMPLETE

- [Fix 1 summary]
- [Fix 2 summary]
  Ready for [next phase/deployment].
  \`\`\`

If any step fails, stop and report the exact error and which step.
```

## How to Order Fixes

Within a prompt, order fixes by dependency first, then priority:

1. Fixes that unblock other fixes (e.g., a database constraint fix before a form fix)
2. P0 Critical bugs
3. P1 High bugs
4. P2 Medium bugs

If fixes are independent, group them by module/file so the agent isn't jumping between files unnecessarily.

## Grouping Into Phases

When there are more than ~6 fixes, split them into phases. Each phase gets its own prompt file. Phases should be:

- **Self-contained** — each phase can be run and verified independently
- **Gated** — each phase has a verification step that must pass before the next phase starts
- **Ordered by impact** — fix what's blocking users first, then fix UX issues, then add features

Name phases with letters (Phase A, Phase B, etc.) and give each a clear theme:

- Phase A: Unblock core workflow
- Phase B: Fix remaining known bugs
- Phase C: Remove UX confusion
- Phase D: Add missing features

## Calibrating for the AI Model

- **Claude Opus** tends to over-engineer. Add explicit "Only make changes directly requested" to Forbidden Actions.
- **Claude Sonnet** is more literal and faster. You can be slightly less verbose in the Steps section.
- When in doubt, be more explicit. An extra sentence of context costs nothing; a misunderstood fix costs a full retry.

## Output

Save the generated prompt as a markdown file. Name it: `[app-name]-phase-[letter]-fix-prompt.md`

At the top, include:

- A one-line instruction: "Paste this entire prompt into Claude Code"
- Prerequisites (what must be done before this prompt)
- Estimated time
