# Accessibility Report

## Scan Attempts
- `@axe-core/cli` on `http://127.0.0.1:8000/` – failed: **cannot find Chrome binary**
- `pa11y` on `http://127.0.0.1:8000/` – failed: **Failed to launch the browser process**

Automated accessibility scans could not run because a headless Chrome/Chromium instance is unavailable in the current environment.

## Manual Review of Login View (`/`)
- The `<html>` tag includes `lang="en"`.
- Heading hierarchy contains a single `<h1>` element.
- Notification container uses `aria-live="polite"` and `aria-label`.

## Recommendations
- Install a headless browser to enable automated Axe or Pa11y scans across all views.
- Verify and adjust color contrast to meet WCAG AA.
- Confirm logical focus order with keyboard navigation.
- Review ARIA attributes to ensure they provide meaningful context without redundancy.
