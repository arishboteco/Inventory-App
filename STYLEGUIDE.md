# Style Guide

This project uses Tailwind CSS and additional utility classes defined in `app.css`.
Follow this guide when building new templates or JavaScript‑driven components.

## Design Tokens

Tokens are provided via CSS variables in `app.css` and extended through
`tailwind.config.js`.

### Colors

| Token | Usage |
|-------|-------|
| `--color-primary` / `primary` | Brand color for buttons, links and highlights |
| `--color-secondary` / `secondary` | Secondary actions and accents |
| `--color-accent` / `accent` | Emphasis elements |
| `--color-danger` / `danger` | Destructive actions |
| `body.light` / `body.dark` | Page background in light/dark mode |
| `bodyText.light` / `bodyText.dark` | Base text color |

### Spacing

Spacing utilities map to CSS variables:

| Tailwind class | Variable |
|----------------|----------|
| `p-0.5` | `--space-0-5` |
| `p-1` | `--space-1` |
| `p-2` | `--space-2` |
| `p-4` | `--space-4` |
| `p-6` | `--space-6` |
| `p-8` | `--space-8` |

### Typography

| Token | Description |
|-------|-------------|
| `--font-size-base` (`text-base`) | Default text size |
| `--font-size-h1` (`text-h1`) | Page titles |
| `--font-size-h2` (`text-h2`) | Section titles |
| `--font-size-badge` (`text-badge`) | Badges and labels |
| Font family | Roboto via Google Fonts |

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

