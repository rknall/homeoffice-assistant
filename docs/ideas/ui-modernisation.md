# UI Modernisation

## Status
Idea - Not Started (separate task after the system cleanup)

## Plugin Candidate
No - Core frontend.

## Problem
The UI grew page by page. Behaviour and look differ between pages: modals do not
all close on Escape or trap focus, row actions are icon-only without labels, and
layouts and spacing are not consistent.

## Proposed Solution
- UI audit of every page, with HTML mockups for the changes and user sign-off
- Modal behaviour: Escape to close, focus trap, focus return, consistent sizing
- Icon-only row actions: labels or tooltips, accessible names
- Use the in-app confirm overlay (introduced with the cleanup, UX-9) as the
  starting point for consistent dialogs

## Implementation Notes
- Run as its own pipeline task (UI design stage, mockups, Playwright comparison).
- Keep Biome accessibility lint clean.

## Related
- [Theming](theming.md)
