# AI Salesman Plugin - Engineering Handoff

Last updated: 2026-07-16

This is the single engineering handoff for the project. Keep it current and concise. Product-facing setup belongs in `README.md`; deployment details belong in `docs/deployment.md`.

## Product Direction

The product is a multi-tenant AI sales platform with three surfaces:

- `plugin/`: Maya, the embedded customer-facing voice/text salesperson.
- `crm/`: the AI Hub admin CRM for clients, data, adapters, usage, conversations, and runtime health.
- `client-panel/`: the authenticated customer workspace for assistant performance and account data.

The product concept is sound. The main architectural weakness is that ecommerce became more mature than other verticals, making product search/cart behavior look like the core product. The target is a universal sales kernel that:

1. understands the customer's goal and intent;
2. extracts entities and constraints;
3. retrieves source-grounded evidence;
4. selects the next sales step;
5. returns a truthful answer and only verified browser actions.

Vertical modules provide capabilities and policies. Deterministic retrieval and validation should handle known catalog, route, entity, and action cases; the LLM should resolve ambiguity and produce natural conversation. Never patch client/demo websites or add site-specific phrases to make a test pass.

## Repository Shape

The project is now one workspace and one deployment artifact:

```text
agent/          Python sales, retrieval, vertical, and orchestration domains
api/            FastAPI routes, runtime, contracts, CRM, and client-panel APIs
client-panel/   Client-facing React workspace
crm/            Admin React CRM
db/             PostgreSQL/pgvector persistence domains
plugin/         Embedded Maya browser runtime
deploy/         Deployment helpers
docker/         Container support
docs/           Deployment and engineering reports
packages/       Shared workspace packages
scripts/        Checks and maintenance utilities
tests/          Python behavioral and integration suites
```

Root files such as `Dockerfile`, `docker-compose.yml`, package/workspace manifests, `requirements.txt`, `pytest.ini`, `README.md`, and environment templates intentionally stay at the root because tools expect them there. Root Python/TypeScript/JavaScript compatibility modules are thin stable entrypoints; implementations live in domain folders.

## Completed

### Modular Refactor

- Split oversized agent, API, database, CRM, plugin, and test modules into domain packages while preserving public imports through compatibility facades.
- Grouped CRM client workspace, shared components, primitives, styles, views, and vertical definitions into focused folders.
- Grouped plugin adapter, runtime, overlay, catalog, audio, session, widget, and core code by ownership.
- Grouped database client, analytics, ecommerce, cache, settings, prompting, knowledge, bootstrap, and runtime code by domain.
- Split the oversized tests by behavior. Every handwritten implementation and test file is currently below 500 lines.
- Removed obsolete scratch scripts and the deleted line-count CSV. Use live line counts instead.

### Behavior And Quality

- Added hybrid lexical, semantic, fuzzy retrieval with Reciprocal Rank Fusion and exact-match prioritization.
- Added deterministic buying-intent regressions for phrases such as `I am interested in buying iPhone` and `Do you sell iPhone?`; these no longer depend on an LLM call or search for literal `% of iphone %` text.
- Grounded product display and comparison wording in selected source rows and improved correction/transcript cleanup.
- Preserved action-truth rules: Maya cannot claim a browser action succeeded without runtime evidence.
- Restored TLS verification by default, bounded audio payloads, protected the crawler trigger, constrained forwarded-IP trust, and added public widget rate limits.
- Client-panel tokens now invalidate after password rotation/revocation.
- Disabled terminal conversation-content logging by default.
- Repaired Python dependency conflicts, added `pip check` and frontend lint to CI, and separated fast and PostgreSQL-backed test commands.
- Applied the local PostgreSQL schema migrations for install credentials and cart session ownership.

### Monorepo And Deployment

- Imported the former sibling `client_panel` project as `client-panel/` in this workspace.
- Updated pnpm workspace scripts, CI, Dockerfile, Docker Compose, API static serving, route tests, ignores, README, and deployment documentation.
- Docker builds no longer depend on a sibling `../client_panel` build context. One repository pull contains the API, plugin, CRM, and client panel.

### Azure Provider And Reference-Site Integration

- Replaced the Groq runtime dependency with one shared Azure OpenAI provider for chat, STT, and TTS. Chat is live-verified; configured audio deployment aliases currently return Azure `404 DeploymentNotFound`, so microphone/speech QA remains blocked on Azure resource deployment rather than application code.
- Added provider-level Azure chat/audio tests and kept secrets out of logs, fixtures, and handoff documentation.
- Corrected product and generic retrieval SQL parameter ordering, and made budget/context follow-ups use the history-augmented query for exact product supplementation.
- Corrected ecommerce type matching so an `iPhone` request does not count Apple accessories as iPhones.
- Grounded a single-product browser action after final product selection so a budget follow-up for iPhone 17 navigates to `shop?q=iphone%2017`, not the broad `electronics` category.
- Enforced disabled conversation-content logging in the orchestrator and transcript diagnostic paths as well as the final turn summary.
- Hardened the independent AI-KART reference storefront in `C:\Users\admin\Desktop\Vercel_website` without adding any Hub-specific integration beyond its single installer `<script>`:
  - normalized 572 products to coherent INR pricing, stock, category, subcategory, and search semantics;
  - limited `iPhone` search results to the four real Apple iPhone models;
  - added a catalog validator and regression tests for pricing, inventory, references, media, and false iPhone taxonomy;
  - moved ignored phone images into tracked catalog media and made the Vercel build copy backend static assets into `dist/static`;
  - added reusable image fallbacks, stock-aware controls, responsive mobile filters/header/hero/product layouts, and stable cart/product behavior;
  - browser-checked home, shop, product, cart, and Hub-widget behavior at desktop plus 320px and 390px mobile widths with no tested horizontal overflow or visible broken images.
- Re-ingested AI-KART through its normal catalog API. A live multi-turn Hub test now finds exactly four iPhones, selects iPhone 17 at INR 79,900 for an under-INR-80,000 follow-up, and explains the choice from source-backed price/stock context.

### UI Review And Redesign

- Compared the CRM with Claimd admin wireframes and the client panel with Claimd portal wireframes from `C:\Users\admin\Desktop\Claimd` only.
- Kept the existing operational information architecture but adopted Claimd's cleaner hierarchy: flatter navigation, tighter spacing, restrained borders, and fewer competing summaries.
- Removed decorative gradients, colored glow rings, blur effects, hover lift, and excessive card shadows.
- Retained Claimd-inspired light and dark token families while making the light theme the default for new sessions; an explicitly saved dark preference is still respected.
- Replaced the CRM's nested sidebar trees with a stable primary navigation and direct drilldowns inside views.
- Simplified the CRM dashboard around an attention queue, provider verification, demand, clients, activity, and health; removed repeated metrics.
- Reworked both login screens into compact operational sign-in surfaces.
- Converted the client panel workspace navigation to a horizontal portal-style bar and removed redundant overview sections and fake simulator content.
- Added persisted light/dark theme controls to both login and authenticated shells. Active navigation and tabs now use transparent or neutral states without colored rails, glow, or tint effects.
- Removed decorative brown/cyan/green insight markers, tinted store-note rows, colored metric rails, decorative KPI bars, and nested metric-card styling from the client panel.
- Flattened CRM quick-health and system-health checks into neutral rows, and converted the dense domain-contract card wall into a bordered, table-like list with plain inline metadata and actions.
- Corrected narrow-screen client controls and tabs so actions stay compact, labels do not overlap, tabs scroll horizontally, and the document does not overflow.
- Standardized both applications on one typography system: the same Inter/Segoe UI fallback stack, 14px regular body text, 13px medium controls, 12px minimum captions, and 600 emphasis reserved for headings, key values, and statuses. Removed arbitrary 700-850 weights and sub-12px UI text.
- Established `#cd96e0` as the shared CRM and client-panel brand color. Light-theme text and links use a darker accessible lavender derivative, while blue, green, amber, and red remain reserved for information, success, warning, and error states.
- Added a restrained supporting data palette using sage `#9cb59b`, sky `#82c8e5`, peach `#ffe5b4`, lavender gray `#c6c1d2`, and cosmic latte `#fafae8`. Repeated live metrics and changing summaries use low-saturation versions of these colors; navigation and static controls remain neutral, while semantic severity colors keep their original meaning.
- Reduced the shared page-title scale to 22px and operational values to 20-26px. Removed remaining 30px-or-larger application text from both frontend style trees, with headings and controls retaining the established 500/600 weight ceiling.
- Added shared pagination with stable-height footers and six-item page sizes to long operational collections. CRM dashboard activity, usage events, domain contracts, clients, data stores, adapters, conversations, and client catalog results are bounded; the client-panel conversation log uses the same page rhythm. Naturally bounded forms and summaries use consistent minimum content heights instead of artificial pagination.
- Applied a shared compact density scale across both applications: smaller shell gutters, topbars, controls, panels, headings, KPI rows, charts, conversation rows, and empty states. Removed forced viewport-height content so short pages no longer stretch merely to fill the screen.
- Rebuilt the CRM dashboard composition around independent main and side columns. Provider usage now spans the full row; demand/activity and client-registry/health stacks size independently, eliminating the large vacant card interiors caused by grid-row stretching.
- Kept CRM Usage metrics at four columns on normal desktop widths and delayed responsive collapse until the content genuinely needs it. Reduced oversized client/readiness/integration/analytics card minimum heights and chart media dimensions across the remaining CRM views.
- Rebalanced all client-panel tabs: three-item briefs fill three equal columns, compact empty states use horizontal rows, Demand health breakdowns sit side by side, and Catalog signals plus opportunities share one side stack instead of leaving a vacant half-row.
- Browser-verified the affected CRM health and client catalog/overview surfaces in light and dark themes at a narrow viewport. Runtime contrast scans reported no visible-text failures, and computed-style checks confirmed no decorative rails or shadows on the changed rows.
- Browser-verified dashboard, usage, health, CRM conversations, and client-panel conversations after the pagination and palette pass. Page navigation changes the visible result window, both themes report zero visible-text contrast failures, and the tested desktop views have no horizontal overflow.
- Browser-verified all five client-panel tabs plus CRM dashboard, usage, conversations, analytics, and health after the supporting-palette and typography pass. Light and dark themes preserve distinct metric colors, no tested view exceeds a 26px operational font size, contrast scans report zero failures, and no tested desktop view overflows horizontally.
- Browser-verified the final density/layout pass at normal 100% desktop scale. CRM dashboard and Usage maintain balanced four-column metrics and independent lower-card stacks; authenticated client Overview, Demand, Conversations, Catalog, and Usage Policy use compact, content-driven heights in light and dark themes.
- Verified CRM and client-panel lint and production builds after the final UI cleanup.
- Fixed the modularized widget bundle path so `/mayabot-adapter.js` and `/mayabot.js` resolve from the repository-root `plugin/` directory; added a path regression test and verified Maya mounts on AI-KART at its registered local origin.

## Verified Baseline

The latest complete local baseline is:

- `606 passed, 1 skipped` with PostgreSQL integration coverage.
- Python compilation succeeds across `agent`, `api`, `db`, and `tests`.
- CRM lint and production build pass.
- Client-panel lint and production build pass from the monorepo.
- Plugin production build passes.
- Shared Python/JavaScript action contracts match across 73 actions.
- `pip check` passes.
- AI-KART catalog validation, two catalog regression tests, frontend lint, TypeScript, and production Vercel build pass. The build includes tracked `/static/catalog/phones/*` assets.

Azure OpenAI chat and live text conversations are verified. Azure STT/TTS are not live-verified because the configured resource reports both audio deployments as missing. Do not describe voice as working until those deployments exist and microphone QA passes.

## Pending Work

### Critical Security And Ownership

1. **Install credential enforcement**
   Issue, rotate, revoke, and verify signed per-install credentials on registration, config, events, assistant HTTP, and WebSocket boundaries. Bind each credential to a tenant and allowed origins. Existing origin checks are containment, not authentication.

2. **Cart session ownership and checkout truth**
   Require a signed session owner, scope every cart query by tenant plus `session_id`, and build checkout invoices only from server-side product/cart rows inside a transaction with row locking and stock validation. The database column exists; API/query enforcement remains.

3. **Tenant data exposure**
   Reduce public catalog/knowledge/status payloads to the minimum widget DTOs and protect private data with the same install credential.

4. **Shared rate limits and privacy controls**
   Move sensitive counters from process memory to a shared store. Add persistence consent, redaction, retention, deletion, and export policy for conversation data.

### Architecture And Reliability

5. **Function-level orchestration cleanup**
   File-level modularity is complete, but 52 Python functions exceed 50 lines. Start with `run_pipeline` and `run_stream_pipeline`, then persistence/retrieval boundaries. Keep orchestrators focused on coordination and move decisions into tested services.

6. **Durable background jobs**
   Move crawl, scan, rehearsal, and smoke work from process-local background tasks/executors to a durable job table/worker with deduplication, retry ownership, status, and cancellation.

7. **Exception and typing cleanup**
   Replace broad `except Exception` handlers at persistence, retrieval, and route boundaries with concrete exceptions and stack-context logging. Finish missing production signature annotations and add Python formatting/lint/type CI gates.

8. **Authenticated client-panel consolidation**
   Continue reducing overlapping identity, security, installer, workspace-map, and next-check sections around the client's common decisions. Authenticated desktop QA is complete; add a dedicated mobile-width authenticated pass without resetting a real client password.

### Maya Product Quality

9. **Universal intent and multi-turn selling**
   Extend deterministic intent/entity handling beyond ecommerce into service discovery, qualification, booking, quote, application, and handoff flows. Persist multi-step state across turns while keeping payment, login, OTP, CAPTCHA, file upload, and sensitive final submits handoff-only.

10. **Retrieval and product detail quality**
    Bias retrieval by intent, route, selected entity, and vertical entity type. Hydrate selected product/entity facts before comparisons and render useful source-grounded recommendations. Say clearly when source data does not contain a requested fact.

11. **Speech uncertainty and action evidence**
    Broaden transcript uncertainty detection and ask a short clarification before acting when no known entity, route, or action matches. Record richer selector, form-field, barrier, and final-DOM evidence.

12. **Live conversational QA**
    After Azure STT/TTS deployments are provisioned, test common natural-language buying phrases, non-ecommerce verticals, 12-20 turn voice sessions, navigation/remount, reconnect, audio state, session continuity, and provider/model behavior. Text chat and the AI-KART iPhone follow-up are already live-verified.

13. **Reference-site redeploy verification**
    Redeploy `C:\Users\admin\Desktop\Vercel_website`, confirm its current public hostname, then verify the built catalog images and 320/390/768/1280 responsive paths over the public URL. The previously supplied `aikart.ergobite.com` hostname did not resolve during this pass; local production-build and browser checks passed.

## Estimate

The original fifth phase is not fully finished. Credential enforcement, cart-session ownership, authenticated client-panel consolidation, orchestration-function cleanup, and live conversational QA remain.

- **6-11 focused engineering days** for the remaining implementation and non-live verification.
- **1-2 additional days** for Azure audio deployment, voice-session QA, and public AI-KART redeploy verification.

## Next Execution Order

1. Re-run and stabilize the monorepo Docker build and full test suite after this UI/structure pass.
2. Enforce install credentials across every public tenant boundary.
3. Enforce cart session ownership and server-authoritative checkout.
4. Complete privacy/shared-rate-limit safeguards.
5. Split the largest orchestration functions in behavior-preserving batches.
6. Consolidate authenticated client-panel workflows and run desktop/mobile QA.
7. Provision/confirm Azure audio deployments, then run live cross-vertical Maya voice testing.
8. Redeploy AI-KART and verify catalog media plus responsive behavior on its confirmed public hostname.

## Verification Commands

```powershell
corepack pnpm install
corepack pnpm -r run build
corepack pnpm --filter ai-hub-crm lint
corepack pnpm --filter client-panel lint
python -m compileall -q agent api db tests
python scripts/check_contracts.py
python -m pytest -q
python -m pip check
docker compose config
docker compose build app
```

Local development:

```text
CRM:          http://127.0.0.1:5174/crm/
API health:   http://127.0.0.1:8585/health
Client panel: http://127.0.0.1:8585/client_panel/<client_id>
```
