# Theming

## Status
Idea - Not Started

## Plugin Candidate
No - Core frontend.

## Problem
Colours are literal Tailwind classes (`gray-*`, `blue-*`) spread over the
components. There is no light/dark mode and no way to change the colour scheme.

## Proposed Solution
- Replace literal gray/blue classes by Tailwind colour tokens (semantic names)
- Light and dark mode following `prefers-color-scheme`, with a theme setting
  (system, light, dark) stored per user
- Optional colour themes built on the same tokens

## Implementation Notes
- Do the token migration first (no visual change), then add the dark palette.
- Plugin frontends use the host styles, so tokens must be available to them.
- Best combined with the [UI modernisation](ui-modernisation.md) audit.

## Related
- [UI Modernisation](ui-modernisation.md)
