# Task History (Archived)

This file is kept for historical reference. Current changes are tracked automatically in `CHANGELOG.md` using `tools/changelog.py`.

## Previous Entries

### 2025-08-29

- Initialized task history and enabled planning.
- Added `TASK_HISTORY.md` for persistent logs.
- Please confirm preferred detail level (all changes vs major milestones).

### 2025-08-28

- Milestone: Phase 1 UI hardening and cleanup
- Highlights: removed tracked `staticfiles/`; pinned Prettier v3.2.5 in hooks; replaced inline `onclick` with `data-*` + delegated events in items table/cards; refined row toggle to ignore link clicks.
- Recent features included: Add Item drawer and Bulk Upload via in-page modal; in-page partial editor for items; table inline editing with select-all and bulk actions; column visibility toggles; cache-busting via `STATIC_VERSION`; exposed `extra_css`/`extra_js` blocks for form styling.

---

Template for future entries (if manual notes are needed):

## YYYY-MM-DD

- Summary: <what changed>
- Files: <key paths touched>
- Notes: <context, follow-ups>
