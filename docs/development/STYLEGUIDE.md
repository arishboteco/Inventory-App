# Style Guide

This project uses Tailwind CSS and additional utility classes defined in [static/css/app.css](static/css/app.css).
Follow this guide when building new templates or JavaScript‑driven components.

## Design Tokens

The canonical tokens are defined in [static/src/tokens.css](static/src/tokens.css). The file is imported by
[static/src/app.css](static/src/app.css) and the variables are referenced in
[Tailwind via `tailwind.config.js`](tailwind.config.js). Updating `tokens.css` propagates color changes
across the application.

> **Note:** Dark mode is temporarily unsupported. All colors must meet WCAG AA contrast requirements on a light background.

### Colors

| Token (CSS / Tailwind) | Light Mode | When to Use |
|------------------------|------------|-------------|
| `body` / `bg-body` | `#ffffff` | Page background |
| `bodyText` / `text-bodyText` | `#111827` | Base text color |
| `--color-primary` / `primary` | `var(--color-primary)` | Links and primary actions |
| `--color-secondary` / `secondary` | `var(--color-secondary)` | Secondary buttons and accents |
| `--color-accent` / `accent` | `var(--color-accent)` | Highlights and callouts |
| `--color-danger` / `danger` | `var(--color-danger)` | Destructive actions |
| `--color-border` / `border` | `var(--color-border)` | Borders and disabled text |

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

#### Usage Rules

- **`text-h1`**: Reserve for the main page title. Only one `text-h1` should appear per page.
- **`text-h2`**: Use for section headings beneath the page title. Maintain sequential order without skipping levels.
- **`text-base`**: Default body copy size. Apply to paragraphs and long-form text for consistent readability.

## Layout & Breakpoints

### Container

- The `.container` utility is centered and applies `var(--space-8)` padding by default.

### Custom `max-*` breakpoints

Use these variants to target smaller viewports:

| Breakpoint | Applies up to |
|------------|---------------|
| `max-sm`   | 639px |
| `max-md`   | 767px |
| `max-lg`   | 1023px |
| `max-xl`   | 1279px |
| `max-2xl`  | 1535px |

## Components

Use the classes in `static/css/app.css` to ensure a consistent look:

- **Buttons**: `.btn-primary`, `.btn-secondary`, `.btn-danger`, `.btn-outline`, `.btn-tertiary`
  - `.btn-outline` – neutral bordered buttons for navigation links or cancel/back actions.
  - `.btn-tertiary` – subtle buttons that blend with form backgrounds for utility actions like export or download.
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

### Buttons

```html
<div class="flex gap-2">
  <button class="btn-primary px-4 py-2 rounded">Primary</button>
  <button class="btn-secondary px-4 py-2 rounded">Secondary</button>
  <button class="btn-danger px-4 py-2 rounded">Danger</button>
</div>

<!-- Hover & focus states -->
<button class="btn-primary px-4 py-2 rounded hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary-dark">Save</button>
```

### Badges

```html
<div class="space-x-2">
  <span class="badge-success">Active</span>
  <span class="badge-warning">Pending</span>
  <span class="badge-error">Failed</span>
</div>

<!-- Hover & focus -->
<span tabindex="0" class="badge-success hover:opacity-80 focus:outline-none focus:ring-2">Hover me</span>
```

### Navigation Button

```html
<a href="#" class="nav-btn hover:bg-primary-dark focus:outline-none focus:ring-2 focus:ring-primary-dark">Dashboard</a>
```

### Table

```html
<table class="table w-full">
  <thead>
    <tr>
      <th class="p-2">Name</th>
      <th class="p-2">Qty</th>
    </tr>
  </thead>
  <tbody>
    <tr class="hover:bg-gray-100 focus:outline-none focus:bg-primary/10" tabindex="0">
      <td class="p-2">Pens</td>
      <td class="p-2">12</td>
    </tr>
  </tbody>
</table>
```

### Form Controls

```html
  <form class="space-y-2">
    <input class="w-full p-2 border hover:border-primary focus:border-primary focus:outline-none" type="text" placeholder="Name" />
    <select class="w-full p-2 border hover:border-primary focus:border-primary focus:outline-none">
      <option>Option A</option>
      <option>Option B</option>
    </select>
    <textarea class="w-full p-2 border hover:border-primary focus:border-primary focus:outline-none" placeholder="Details"></textarea>
  </form>
```

## Accessibility

- Color variables in `static/css/app.css` are tuned for high contrast on light backgrounds. Ensure text and UI elements meet WCAG AA contrast ratios.
- Interactive components must include the 2px focus ring styles defined in `static/css/app.css` (e.g., button and form control focus states) to remain keyboard accessible.

## Guidelines

- Prefer Tailwind utility classes for layout and spacing.
- Reuse predefined components from `static/css/app.css` instead of creating new custom styles.
- Keep responsive behaviour explicit using custom `max-*` breakpoints defined in `tailwind.config.js`.
- When adding new templates or JavaScript‑driven components, always apply Tailwind
  utilities and existing `static/css/app.css` classes before introducing custom CSS.

