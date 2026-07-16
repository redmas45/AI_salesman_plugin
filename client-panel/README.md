# Client Panel

Tenant-facing analytics and usage workspace served by the AI Hub FastAPI app at
`/client_panel/<site_id>/`.

## Ownership

- `client-panel/` owns the React UI.
- `api/client_panels/` owns authentication and dashboard APIs.
- `db/client_domain/panel/` owns tenant-scoped persistence.
- The root Docker build compiles this package and copies `dist` into the runtime
  image. No sibling repository is required.

## Commands

Run from the repository root:

```powershell
corepack pnpm --filter client-panel dev
corepack pnpm --filter client-panel lint
corepack pnpm --filter client-panel build
```

The development server defaults to `http://127.0.0.1:5177`. Set
`VITE_CLIENT_PANEL_BASE_PATH=/client_panel/` when validating the production
route shape.

## Structure

```text
src/
  components/  Shared panel components
  styles/      Feature-scoped CSS
  views/       Top-level workspace tabs
  api.ts       Tenant API client
  App.tsx      Authentication and data-loading shell
```

Client-panel access is tenant-scoped. Never expose cross-client CRM data or use
the CRM admin token as a client credential.
