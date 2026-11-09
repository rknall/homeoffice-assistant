# Example plugin

A small plugin that shows the pieces a HomeOffice Assistant plugin can provide.
Use it as a reference, not as a template to copy verbatim.

## Layout

- `plugin.manifest.json`: plugin id, version, capabilities, required and
  provided permissions.
- `backend/`: the `BasePlugin` subclass (`plugin.py`), API routes (`routes.py`)
  and the plugin's own Alembic migrations (`migrations/`).
- `frontend/index.js`: the frontend module, loaded by the host at runtime.

## Frontend module

`frontend/index.js` is hand-written plain JavaScript on purpose. The host loads
`plugins/<id>/frontend/index.js` as an ES module and reads these exports:

- `manifest`
- `getNavItems()` for sidebar entries
- `getRoutes()` for pages, prefixed with `/plugins/<id>`
- `widgets` for host slots (`dashboard`, `eventDetail`, `companyDetail`)
- `onLoad()` and `onUnload()`

The example has no build step. It takes React from `window.React` (the host
exposes it) and builds elements with `React.createElement` instead of JSX. That
keeps it readable without tooling, but it also means no type checking.

The time-tracking plugin shows the typed alternative. It is written in
TypeScript with JSX under `plugins/time-tracking/frontend/`, and
`bun run build:plugins` in `frontend/` bundles every `plugins/*/frontend/index.ts`
into `index.js`. `frontend/tsconfig.plugins.json` type-checks those sources as
part of `bun run build`. A plugin that wants types should follow that layout
rather than this one. Converting the example is not planned.

## Host API

Bundles only import `react`. Anything else the host offers is on `window.hoaHost`
(currently `confirmAction`). The time-tracking plugin wraps it in
`frontend/host.ts`.
