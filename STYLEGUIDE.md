# Style Guide

This project uses Tailwind CSS and additional utility classes defined in [app.css](app.css).
Follow this guide when building new templates or JavaScript‑driven components.

## Design Tokens

Tokens are provided via CSS variables in [app.css](app.css) and surfaced to
[Tailwind via `tailwind.config.js`](tailwind.config.js).

### Colors

| Token (CSS / Tailwind) | Light Mode | Dark Mode | When to Use |
|------------------------|------------|-----------|-------------|
| `body` / `bg-body-light`, `bg-body-dark` | `#ffffff` | `#0f172a` | Page background |
| `bodyText` / `text-bodyText-light`, `text-bodyText-dark` | `#111827` | `#f8fafc` | Base text color |
| `--color-primary` / `primary` | `var(--color-primary)` | `var(--color-primary-dark)` | Links and primary actions |
| `--color-secondary` / `secondary` | `var(--color-secondary)` | `var(--color-secondary)` | Secondary buttons and accents |
| `--color-accent` / `accent` | `var(--color-accent)` | `var(--color-accent)` | Highlights and callouts |
| `--color-danger` / `danger` | `var(--color-danger)` | `var(--color-danger)` | Destructive actions |

### Spacing

Spacing utilities map to CSS variables and are mode‑independent:

| Token (Tailwind / CSS) | When to Use |
|------------------------|-------------|
| `p-0.5` / `--space-0-5` | Hairline gaps and subtle adjustments |
| `p-1` / `--space-1` | Tight spacing around small elements |
| `p-2` / `--space-2` | Default padding for compact components |
| `p-4` / `--space-4` | Standard padding and grid gaps |
| `p-6` / `--space-6` | Large section spacing |
| `p-8` / `--space-8` | Layout gutters and container padding |

### Typography

| Token (Tailwind / CSS) | When to Use |
|------------------------|-------------|
| `text-base` / `--font-size-base` | Body copy |
| `text-h1` / `--font-size-h1` | Page titles |
| `text-h2` / `--font-size-h2` | Section headings |
| `text-badge` / `--font-size-badge` | Badges and labels |
| Font family `sans` | Roboto via Google Fonts for all text |

## Components

Use the classes in `app.css` to ensure a consistent look:

- **Buttons**: `.btn-primary`, `.btn-secondary`, `.btn-danger`
- **Status badges**: `.badge-success`, `.badge-warning`, `.badge-error`
- **Navigation buttons**: `.nav-btn`
- **Tables**: `.table`
- **Forms**: base styles are applied to `input`, `select` and `textarea`

## Usage Examples

### Responsive Grid

```html
<div class="grid grid-cols-4 max-md:grid-cols-1 gap-4">
  <div class="p-4 bg-primary text-white">1</div>
  <div class="p-4 bg-secondary text-white">2</div>
  <div class="p-4 bg-accent text-white">3</div>
  <div class="p-4 bg-primary text-white">4</div>
</div>
```

### Button

```html
<button class="btn-primary px-4 py-2 rounded">Save</button>
```

### Form Input

```html
<input class="w-full p-2" type="text" placeholder="Search" />
```

### Predictive Dropdown

```html
<select class="predictive w-full">
  <option>Item A</option>
  <option>Item B</option>
</select>
```

## Guidelines

- Prefer Tailwind utility classes for layout and spacing.
- Reuse predefined components from `app.css` instead of creating new custom styles.
- Keep responsive behaviour explicit using custom `max-*` breakpoints defined in `tailwind.config.js`.
- When adding new templates or JavaScript‑driven components, always apply Tailwind
  utilities and existing `app.css` classes before introducing custom CSS.

