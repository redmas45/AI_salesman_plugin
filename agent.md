# AI Salesman Plugin - Current Handoff

Last updated: 2026-07-03 12:45 IST

This file is the working handoff only. Keep README as the product document. Keep this file short, current, and focused on what the next engineer/session needs.

## Non-Negotiable Rules

- Fix AI Hub, Maya, CRM, runtime discovery, prompts, RAG, adapters, and tests. Do not patch client websites to make demos pass.
- All behavior must stay universal across verticals. No Policy, AI-KART, travel, insurance, ecommerce, or port-specific hacks.
- Maya must not say an action happened unless browser/runtime evidence proves it happened.
- Tenant data remains isolated per client. PostgreSQL + pgvector stay the primary data/RAG foundation.
- README is product-facing. Operational issues, pending fixes, and next-session notes belong here.
- `agent.md` must stay a concise handoff, not a historical dump. Delete stale notes as work completes or becomes irrelevant.
- Relevant local client projects for current testing are only `Vercel_website` aka AI-KART and `Policy_website`.

## Completed Recently

- **Hybrid RAG Search Engine (RRF):** Rewrote product and knowledge search in [rag.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/agent/rag.py) and [generic_rag.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/agent/retrieval/generic_rag.py) using lexical, semantic, and fuzzy typo searches run in parallel, merged via Reciprocal Rank Fusion (RRF) for immediate exact match prioritization. Placed GIN/trigram migrations at correct index creation orders and forced vector/trigram extensions to the public schema to ensure global visibility across dynamically generated tenant schemas.
- **OpenAI Voice/TTS Switch:** Configured OpenAI as the primary client for STT/TTS in [.env](file:///c:/Users/admin/Desktop/AI_salesman_plugin/.env) to resolve voiceless Groq outages.
- **Voice Query Cleanup + Grounded Product Display:** Cleaned speech filler/correction terms such as "okay we iphone" and "I asked for books" before product search/navigation, bypassed stale ecommerce discovery cache for correction turns, and rewrote product display responses from the selected retrieved rows so Maya does not speak conflicting product names/prices.
- **Product Response Service Extraction:** Moved ecommerce search-query cleanup, product fact formatting, cart confirmation text, and display-response grounding from `agent/orchestrator.py` into class-based services in [product_response.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/agent/product_response.py).
- **Product Matching Service Extraction:** Moved exact catalog matching, brand/type fallback, inventory category lookup, and history product recovery into class-based [product_matching.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/agent/product_matching.py). `orchestrator.py` now delegates through compatibility wrappers for existing tests.
- **CRM Password Fix + UI Cleanup:** Fixed client-panel password updates failing after DB write because `db/clients.py` referenced token-limit variables inside the password audit block. The CRM modal now uses the backend generator, shows/copies the newly-current password after set/generate, and explains that previously stored PBKDF2 passwords cannot be recovered. The client operator header and primary setup button were also cleaned up; the setup button now says `Setup`.
- **Durable Auto-Approval:** Action candidates discovered with confidence `>= 75%` are automatically approved and written to the active configurations in [clients.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/db/clients.py).
- **Simplified CRM Adapter Interface:** Reorganized [AdapterTab.tsx](file:///c:/Users/admin/Desktop/AI_salesman_plugin/crm/src/views/client-workspace/AdapterTab.tsx) to hide detailed diagnostic logs behind an "Advanced Diagnostics" toggle and filter candidate actions to only show pending options.
- **Secure Password Dialog:** Implemented a password visibility toggle (eye icon) and validated the generation and setting flows in [Dialogs.tsx](file:///c:/Users/admin/Desktop/AI_salesman_plugin/crm/src/components/shared/Dialogs.tsx).
- **Paired Search & Navigation:** Paired RAG product search displays with browser `NAVIGATE_TO` page actions to `shop?q=<query>` in [orchestrator.py](file:///c:/Users/admin/Desktop/AI_salesman_plugin/agent/orchestrator.py) (bypassed in pytest to keep legacy regressions passing).
- Setup run stop/cancel/timeout safety is implemented with CRM `Stop setup`, cooperative cancellation, stale-run expiry, and duplicate-run blocking.
- Browser action truth loop is implemented across HTTP/SSE/WS: `request_id`, `turn_id`, `sequence`, browser requested/executing/terminal telemetry, CRM conversation evidence, and rebuilt `mayabot.js`/`mayabot-adapter.js`.
- Runtime action events are now durable server-owned Postgres rows in `hub_action_events`.
- Audit events now persist key browser/runtime/admin/setup/prompt/quota events in `hub_audit_events`.
- CRM conversation/action evidence now reads durable action rows, not old JSON history.

## Verification

Ran successfully:

```powershell
python -m pytest -q
python -m pytest tests\test_crm_token_limits.py tests\test_orchestrator_matching.py -q
python -m compileall agent api db tests
corepack pnpm --filter ai-hub-crm exec tsc -b
```

Results:

- Python pytest suite: `544 passed, 1 skipped` in `70.85s`
- Focused password/orchestrator regression tests: `73 passed` in `16.21s`
- Python compile check passed.
- CRM TypeScript build check passed through Corepack. The root `pnpm run typecheck` script still fails on this machine because the plain `pnpm` shim is not on PATH; direct `corepack pnpm ...` works.

## Current Architecture Review

Refreshed file-wise line counts are in [loc_by_file.csv](file:///c:/Users/admin/Desktop/AI_salesman_plugin/loc_by_file.csv). The project is not fully compliant with the new 500-line budget yet.

Largest remaining offenders:

- `crm/src/index.css`: 8,059 lines
- `agent/orchestrator.py`: 3,618 lines
- `crm/src/views/ClientDetailView.tsx`: 3,451 lines
- `db/clients.py`: 3,203 lines
- `agent/ingestion.py`: 2,274 lines

Next refactor should split `db/clients.py` into client repository, audit service, password service, runtime status service, and serialization modules; split `ClientDetailView.tsx` into tab components/hooks; and split `index.css` into CRM shell, modal, client workspace, table, and utility stylesheets.

## Current Pending Queue

1. Manual long voice-session validation
   - User will manually test 12-20 turn voice sessions.
   - Still watch WebSocket reconnect, page navigation/remount after product search, audio playback state, session ID continuity, and mic readiness after multiple actions.

2. Richer browser action evidence
   - Durable action rows are in place.
   - Still expand evidence for clicked selector/label, submitted form fields, missing required fields, blocked provider boundaries, and final DOM state.

3. Universal flow planner next layer
   - Foundation is implemented.
   - Still add multi-step state persistence for checkout/quote/booking/application flows across turns.
   - Payment, login, OTP, CAPTCHA, file upload, and final sensitive submits must remain handoff/prepare-only.

4. Product detail hydration and comparison quality
   - Text fallback is source-grounded from retrieved products/entities.
   - Still add a universal hydration step before product detail and comparison answers: fetch selected product IDs, variants/options/sizes, attributes/specs, tags, review aggregates/snippets when available, and inject that compact source block into Maya's prompt.
   - If a requested detail is not in client/source data, Maya must say the website does not provide it and offer to compare available buying facts instead.
   - Still render a useful comparison table/card, preserve product/page sync, and end with a recommendation tied to user needs.

5. STT uncertainty and transcript repair
   - Incomplete filler clarification and ecommerce search-query cleanup are implemented.
   - Still broaden weird-transcript detection outside obvious product search/correction phrases and ask a short clarification before acting when there is no known entity/route/action match.

6. Retrieval and answer relevance
   - Bias retrieval by current intent, route, selected entity, and vertical entity type.
   - Avoid mixing unrelated categories unless the user asks for broad alternatives.

7. Capability report repair UX
   - Smoke failures now have specific runtime filter diagnosis.
   - Missing expected actions such as `REQUEST_CALLBACK` still need specific candidate-route/form diagnosis, not only "Run setup".
   - Show expected action, candidate labels/routes/forms, confidence reason, repair attempt, and admin repair/ignore controls.

8. Typed API client next step
   - Shared TS contracts exist for action names/statuses.
   - Still add generated/OpenAPI typed API client for CRM DTOs, runtime config, usage rows, conversation rows, and capability reports.

9. Whole-codebase modular refactor
   - Current LOC review shows the codebase is still too monolithic and hard to maintain.
   - Later refactor must split oversized Python/TS/CSS files into domain modules with clear classes, services, repositories, functions, and typed interfaces.
   - Python priority: use OOP where it creates real ownership boundaries, especially for orchestration, ingestion, client persistence, security/auth, and product/knowledge retrieval.
   - Keep behavior universal and covered by regression tests during the refactor; do not rewrite by demo-site patching.

10. Stronger tenant and install-script security
   - Client panel is password protected, but later security work must ensure a client can only open its own panel/data.
   - Add stronger tenant authorization on every client-panel API call, not only UI routing.
   - Protect the one-line install script from being copied to unauthorized websites. Candidate solutions to evaluate: per-client signed install tokens, allowed-origin/domain allowlists, server-side origin enforcement, short-lived signed widget config, install-script key rotation/revocation, abuse rate limits, audit logging, and CRM warnings for unknown origins.
   - The final design must support independent client websites hosted on different domains while keeping AI Hub as the central CRM.

## Useful Local Commands

```powershell
corepack pnpm install
corepack pnpm -r run build
python scripts/check_contracts.py
python -m pytest -q
docker compose up -d --build
```

CRM:

```text
http://127.0.0.1:5176/crm/
```

AI-KART local test site:

```powershell
cd C:\Users\admin\Desktop\Vercel_website\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd C:\Users\admin\Desktop\Vercel_website\frontend
npm run dev -- --host 0.0.0.0 --port 5175
```

Policy local test site:

```powershell
cd C:\Users\admin\Desktop\Policy_website\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003

cd C:\Users\admin\Desktop\Policy_website\frontend
npm run dev -- --host 0.0.0.0 --port 5183
```
