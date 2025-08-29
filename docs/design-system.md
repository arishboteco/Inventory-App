# Design System

This project uses a small design system shared between code and design tools.

## Tokens

Core design tokens are centralized in [`static/css/_variables.scss`](../static/css/_variables.scss). These CSS variables define the
application's colors, typography scale, and spacing values.

Use them in stylesheets or inline styles via the `var()` function:

```css
.button {
  background-color: var(--color-primary);
  padding: var(--space-2) var(--space-4);
}
```

Changing a token in `_variables.scss` updates the value across the codebase.

## Figma Component Library

A reusable Figma component library mirrors these code components. When updating a component or token:

1. Update `_variables.scss` and relevant code.
2. Reflect the change in the shared Figma library so designs stay in sync.
3. Use the Figma components when designing new screens to ensure parity with code.

The Figma library can be found in the team's shared workspace.
