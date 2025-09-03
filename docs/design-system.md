# Design System

This project uses a small design system shared between code and design tools.

## Tokens

Core design tokens are centralized in `tailwind.config.js` under `theme.extend`. These values define the
application's colors, fluid typography scale (using `clamp()` for responsive sizing), and spacing values.

Use them in stylesheets via Tailwind utility classes or the `theme()` function:

```css
.button {
  @apply bg-primary py-2 px-4;
}
```

Updating a token in `tailwind.config.js` applies the change across the codebase.

## Accessible Color Combinations

The following token pairs meet WCAG AA (4.5:1) contrast requirements:

| Background token        | Text token             | Contrast ratio |
| ----------------------- | ---------------------- | -------------- |
| `primary` (`#2563EB`)   | `nav` (`#FFFFFF`)      | 5.17:1         |
| `secondary` (`#15803D`) | `nav` (`#FFFFFF`)      | 5.02:1         |
| `accent` (`#B45309`)    | `nav` (`#FFFFFF`)      | 5.02:1         |
| `body` (`#FFFFFF`)      | `bodyText` (`#111827`) | 14.00:1        |

Use these pairings for buttons, links, and surfaces to ensure sufficient contrast.

## Figma Component Library

A reusable Figma component library mirrors these code components. When updating a component or token:

1. Update `tailwind.config.js` and relevant code.
2. Reflect the change in the shared Figma library so designs stay in sync.
3. Use the Figma components when designing new screens to ensure parity with code.

The Figma library can be found in the team's shared workspace.
