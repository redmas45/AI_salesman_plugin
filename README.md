# AI Salesman Hub

AI Salesman Hub is the central "mothership" for AI assistants on client websites. A client website should only need one script tag. The Hub owns the widget, adapter runtime, crawling, vertical detection, prompt profiles, RAG/catalog ingestion, CRM, analytics, and Client Panel APIs.

The client website stays independent. It owns its own users, products or business records, checkout or booking flows, admin system, and public pages.

## Current State

Current development checkpoint: **L15 universal runtime intelligence, tenant cache, data freshness, and voice/provider hardening**

Last code change: **2026-07-16** (`d9ef17b`)

Last verified: **2026-07-29**

```text
python -m pytest -q                          -> 643 passed, 1 skipped (~4m40s)
python -m compileall agent api db tests       -> passed
corepack pnpm run contracts:check             -> 73 actions matched
corepack pnpm --filter ai-hub-crm lint        -> clean
corepack pnpm --filter client-panel lint      -> clean
corepack pnpm -r run build                    -> crm, client-panel, plugin, contracts all built
```

This repo has moved past the old ecommerce-only baseline. The current foundation supports:

- Universal one-line installer: `/install.js` with automatic client identity and vertical discovery.
- Hosted browser adapter runtime: `/mayabot-adapter.js`.
- Hosted widget bundle: `/mayabot.js` and `/mayabot-widget.js`.
- Browser discovery beacon: `POST /v1/widget/register`.
- Browser-side hard-widget/provider hints for auth gates, CAPTCHA, payment providers, calendar widgets, maps, file uploads, iframes, and external handoffs.
- Safe provider handoff execution for map links/embeds, appointment scheduler links/embeds, and contact providers such as phone, email, and WhatsApp-style links.
- Automatic client bootstrap when an installed site is first seen.
- Deterministic vertical classification across ecommerce, travel, insurance, finance, healthcare, food, real estate, education, automotive, legal services, jobs, events/ticketing, construction, and generic websites.
- Generated adapter runtime config for routes, selectors, actions, platform hints, and discovery metadata.
- Admin-visible live action candidates from buttons, links, forms, routes, and generated action mappings.
- CRM approval/rejection controls for live action candidates and repair proposals, with review history preserved in client runtime config.
- Per-client tenant schemas for crawled data, knowledge, embeddings, data versions, and answer cache state.
- Bounded Maya session memory with rolling summaries, recent turns, retrieved site context, and explicit answer scopes.
- Tenant-local safe answer cache for repeated grounded questions, with bypasses for cart, checkout, quote, booking, payment, login, upload, and other side-effect actions.

## Recent Enhancements (2026-07-16)

- **Explicit provider readiness**: `/health` now reports a `provider_status` field derived from a real verification of the configured Azure chat, STT, and TTS deployments. `check_azure_openai_runtime()` exercises all three; failures are classified as `auth_error`, `quota_exhausted`, or `runtime_error`.
- **Provider status expires**: A successful verification is only trusted for 15 minutes (`PROVIDER_VERIFICATION_MAX_AGE_SECONDS`). After that the status falls back to `unverified` instead of showing a stale green light. CRM must re-check via `POST /v1/admin/provider-usage/check`.
- **Persisted provider events**: Provider failures and recoveries are written to `hub_provider_events` and surfaced in the CRM dashboard, with an in-process ring buffer as fallback when the database is unreachable.
- **CIDR-aware trusted proxies**: The rate limiter previously matched `TRUSTED_PROXY_IPS` by exact string. It now parses entries as IP networks, so `10.0.0.0/8`-style ranges work and malformed entries are logged and ignored instead of silently trusting nothing. `TRUSTED_PROXY_IPS` is now wired through `docker-compose.yml`.
- **Browser speech fallback is honest**: `speakText()` now returns a boolean and refuses to claim success when no voice is available, so the widget can fall back to server TTS instead of going silent. The female-voice hint list was widened across Windows, macOS, and cloud voice names.
- **Audio diagnostics and widget stability**: Reworked recorder/playback lifecycle and widget styles to survive long voice sessions and repeated page transitions.

## Recent Enhancements (2026-07-01)

- **Universal schema-driven prompt contract**: Runtime and CRM-generated prompts now require Maya to extract facts from the latest message, conversation history, session profile, live page context, and the discovered action field schema before asking follow-up questions.
- **No site or vertical hot patches**: Prompt/action fixes must use discovered action names, required params, field labels, input types, placeholders, and select/radio options from the current website. Do not add Policy, AI-KART, travel, insurance, or any other domain-specific slot patches to make one demo pass.
- **Backend action-param guard**: The orchestrator now fills action params from natural language using each site's discovered action schema before capability filtering, so a weak LLM action can still execute with discovered form fields instead of getting blocked for missing params.
- **Exact missing-field questions**: Capability filtering now asks for the exact missing required field, such as age or phone, instead of falling back to a broad vertical intake question.
- **Quote intent over page navigation**: Phrases such as "show me quotes" are treated as quote-flow intent when the site supports `START_QUOTE`; explicit requests like "open quote page" still navigate.
- **Result-form action contracts**: Safe result-producing forms such as quote/search/availability forms now treat their discovered fields as required action params, even when the DOM omits HTML `required`; sensitive/contact/finalization forms remain prepare-only.
- **Schema-derived setup smoke tests**: Setup prompt checks now prefer deterministic contract tests generated from each action's discovered required fields. Fallback LLM smoke tests are enriched with exact field values from the same schema so setup validates the current website contract instead of a canned vertical script.
- **Safer rediscovery vertical handling**: Existing clients keep their current vertical when a weak generic rediscovery refreshes the URL/origin, while the normal confidence gate still controls real vertical upgrades or switches.
- **Sales relevance and answer scope**: Maya now marks every response as `grounded_fact`, `buying_guidance`, `website_action`, or `unsupported_or_offsite`. Buying-relevant questions use source data; off-site deep theory is bounded unless the current website's retrieved data supports it.
- **Bounded session context**: Runtime calls include a compact rolling session summary plus recent turns instead of an unbounded transcript. This keeps Maya conversational without wasting tokens or repeating already supplied facts.
- **Tenant-local answer cache**: Safe, source-backed answers can be served from a per-client cache when the same question returns under the same tenant data version. Side-effect requests always bypass cache.
- **Dynamic data versioning**: Catalog, knowledge, prompt-profile, and runtime-config changes bump the tenant data version and stale old cache rows, so a changed inventory or plan catalog does not leave Maya answering from old data.
- **CRM cache visibility**: Dashboard and client cards expose cache hits, fresh cache rows, and estimated tokens saved. The admin API exposes `/v1/admin/clients/{site_id}/answer-cache`.
- **Extended tenant isolation audit**: The isolation check now covers answer-cache scope in addition to runtime config, install script scoping, prompt profile scoping, and knowledge/RAG scoping.

## UX Reality Check And Recovery Plan (2026-07-02)

Recent local testing shows the system is not yet close to the target end-user quality. Maya can often produce an action, but the full buyer journey is not reliable enough. The next work session must focus on end-to-end user experience, not more surface-level prompt edits.

Observed from recent Docker logs:

- Maya emits actions such as `NAVIGATE_TO`, `START_QUOTE`, `SHOW_ENTITIES`, `SORT_ENTITIES`, and `COMPARE_ENTITIES`, but the backend log does not prove that the browser completed the action, changed page, submitted a form, or recovered after failure.
- WebSocket voice sessions close and reopen repeatedly during one user journey. The mic/voice lifecycle needs a long-session stability pass.
- Purchase intent is weak. Example: asking to buy a named travel plan produced navigation to the travel route, then later fell back to a generic quote flow using old age/city facts. A purchase journey must bind to the specific item or service the user named.
- Comparison is shallow and sometimes wrong. Example: unclear speech triggered entity comparison, and a two-plan comparison included extra records. Compare output must be source-grounded, structured, and useful for deciding what to buy.
- Recommendation output can be irrelevant or mixed across categories. Example: a health-insurance-style question returned motor/health records without a clear conclusion.
- Speech recognition errors such as `SDFC`, `SPI`, or unrelated phrases are not handled with enough disambiguation before Maya acts.

Tomorrow's priority plan:

1. **Action truth loop**: Add a generic request/ack contract between Maya and the browser adapter. Every UI action gets an ID, browser execution result, URL/DOM/form evidence, and failure reason. Maya must not claim "opened", "started", "added", or "submitted" unless the browser confirms it.
2. **Mic and session stability**: Test and fix long conversations across many turns, page navigations, widget reloads, WebSocket reconnects, recording state, audio playback, and status polling. The target is a stable voice session through a realistic buying journey.
3. **Purchase flow planner**: Build a universal flow planner for `buy`, `add to cart`, `book`, `apply`, `quote`, and `checkout` intents. It must resolve the named entity, choose the safest next website action, execute or hand off based on risk, and avoid falling back to generic navigation.
4. **Comparison quality layer**: Replace generic compare behavior with a structured source-grounded comparison model: matched items only, key decision dimensions, missing-data labels, best-fit recommendation, and no off-site speculation.
5. **STT uncertainty guard**: Detect low-confidence or semantically odd transcripts before acting. Ask one short clarification when the transcript conflicts with page/site data or likely entity names.
6. **End-to-end acceptance tests**: Add browser tests for navigation, quote submission, add-to-cart/purchase prep, comparison, sorting, and long mic sessions across ecommerce and insurance fixtures. A setup run is not green unless browser-executed action evidence passes.
7. **CRM observability**: Surface action execution status in the CRM conversation/activity view: requested action, browser ack, final URL, form submit result, latency, and failure reason.
Golden rule: fixes must remain universal and runtime-discovered. Do not patch AI-KART, Policy Website, travel, insurance, or any individual client website to make one demo pass.

## Recent Enhancements (2026-06-29)

- **Widget Runtime Readiness**: Added missing AI hub widget runtime paths (`/v1/shop`, `/v1/shop/stream`, `/v1/ws/shop`, `/ws/chat`) to the public CORS whitelist to allow proper widget integration across external client websites.
- **Docker Cache Optimization**: Separated massive dependencies (PyTorch CPU, Playwright, Crawl4AI) into a dedicated pre-requirements layer in the `Dockerfile`. This preserves the 3GB cache layer across Python file and requirement updates, dramatically reducing rebuild times.
- **Dynamic LLM Smoke Tests**: Setup can generate domain-aware smoke tests with `gpt-4o` from the client's vertical/runtime context, with deterministic vertical-specific fallback tests for every supported README vertical. Unit/regression tests and quota-limited environments do not depend on external LLM calls for smoke-case generation.
- **Autonomous Auto-Healing Setup**: The setup phase is now a self-healing loop. If a smoke test fails (e.g., action mismatch or data fallback), the system autonomously diagnoses the failure, uses an LLM to generate a developer rule for the prompt profile, and retries the test until it succeeds. Setup times are tracked, and website drift automatically flags a site as needing re-setup. During auto-repair, LLM-generated developer rules bypassing the AI's base policy are prefixed with `[CRITICAL OVERRIDE RULE]` so that the system correctly forces the agent to follow them, preventing infinite retry loops.
- **CRM Client Security**: Added a "Security & Access" section to the Client Overview tab where admins can view the initial randomized client panel password and quickly reset it.
- **CRM Duplicate Installs UI**: Enhanced the `ClientsView` component to intelligently hide duplicate `auto_*` dynamically generated installations when an active, explicitly set client (like `ai_kart`) is already running on the same origin (including resolving localhost domain aliases like `host.docker.internal`).
- **Universal Domain Readiness Matrix**: Added an automated gate for every README vertical that checks discovery profile actions survive capability filtering, deterministic setup smoke cases request valid/allowed actions, and non-commerce source-backed fact answers still show retrieved records when the LLM gives a weak answer.
- **Browser Runtime Action Execution Gate**: Added a browser-level regression that loads the hosted adapter bundle, sends a server-style generated `START_QUOTE` action with runtime sequence params, and verifies the website form submits and navigates to the quote-results route.
- Immediate prompt suggestions from first-page discovery before deeper flow discovery runs.
- CRM Prompt tab can promote discovered prompt suggestions into editable developer rules for admin review.
- Vertical-aware sales intake questions for ecommerce, insurance, travel, finance, healthcare, food, real estate, education, automotive, legal, recruiting, events, construction, and generic sites.
- CRM Prompt tab shows generated sales intake questions so admins can review what the assistant will ask before starting flows.
- Action-readiness summaries connect generated form/sequence actions to required params and the intake question that should collect them before execution.
- Runtime repair proposals from action health, validation evidence, and high-confidence action candidates.
- Tenant isolation audit endpoint for checking client runtime config, install script scoping, prompt profile scoping, and knowledge/RAG scoping.
- Robots/sitemap-aware HTTP crawl fallback that prioritizes high-value URLs and respects discovered disallow rules.
- Deterministic multi-domain discovery fixtures for 13 vertical patterns, including construction.
- Provider-heavy multi-domain discovery fixtures for payment, scheduler, CAPTCHA, auth, upload, iframe, map, and external-provider boundaries.
- Generic same-origin DOM sequence runner for bounded actions such as fill, click, select, submit, wait, scroll, and navigate.
- Shared browser target resolver for stale selectors, with fallback matching by label, text, field name, placeholder, role, and nearest form.
- Deep DOM traversal for open shadow roots and same-origin iframe documents during discovery, action execution, validation, barrier hints, and async rediscovery.
- Shared custom-control selectors for ARIA buttons, links, menu items, tabs, options, comboboxes, searchboxes, textboxes, and contenteditable fields.
- User-like browser event driver for focus, scroll, pointer/mouse activation, keyboard activation, text entry, checkbox state, select options, and form submit.
- Runtime action execution telemetry for success, failure, blocked, and fallback-stage outcomes, visible in CRM and preserved across rediscovery.
- Generic entity lookup and widget rendering for non-commerce RAG actions such as `SHOW_ENTITIES`, `COMPARE_ENTITIES`, and `OPEN_ENTITY_DETAIL`.
- First-load runtime config refresh after browser registration, so a newly pasted script does not need a page reload to use generated config.
- SPA route-change rediscovery for `pushState`, `replaceState`, `popstate`, and hash navigation.
- Debounced async DOM rediscovery for late-loaded buttons, forms, iframes, and fields after SPA hydration or widget injection.
- Rediscovery-safe config merging, so late page observations update routes/actions without wiping learned interactions, CRM overrides, validation, flow, rehearsal, regression, prompt suggestions, or barrier policy evidence.
- Privacy-safe interaction learning from same-origin clicks and form submits, stored as recent interaction traces and action candidates.
- Vertical-aware interaction-to-action learning that can promote high-confidence observed buttons/forms into safe per-client adapter actions without replacing manual CRM overrides.
- CRM vertical selector and vertical-aware client workspace labels/tabs.
- CRM Adapter tab showing the generated adapter code and runtime config for each client.
- CRM Prompt tab for draft/published prompt profile editing and version history.
- Generic knowledge tables, product-to-knowledge sync, and public exact-ID entity lookup for non-commerce RAG.
- Existing AI-KART ecommerce behavior preserved.
- Current CRM operation model:
  - script-detected sites stay Available until explicitly approved
  - Available installs are grouped by online/offline reachability
  - duplicate `auto_*` installs are hidden when an explicit installer `data-site-id` exists on the same origin
  - `Remove` hides an install from CRM lists by marking it deleted while retaining tenant data; `Move to available` is a separate lifecycle action for current clients
  - setup is the single visible operator action for crawl, flow discovery, rehearsal, readiness evidence, and prompt smoke tests
  - crawl/setup stay locked while the source website is offline
- Universal action execution rule:
  - setup/discovery must never depend on client-specific website patches or hardcoded site IDs
  - prompt engineering must be schema-driven: extract and ask for fields from the current website's discovered action contract, not from hand-written assumptions about a domain
  - safe information, comparison, sorting, page-opening, and chat-session actions are derived from the shared action registry instead of hand-maintained per-vertical allowlists
  - low-sensitivity result forms, such as search, availability, calculator, and quote-results forms, may be submitted when their labels indicate they show options/results and their fields do not collect contact, payment, identity, upload, medical, application, or other sensitive/finalization data
  - lead capture, checkout, booking finalization, payment, application, claim, renewal, contact, and sensitive forms stay prepare-only or handoff-first until the website/provider/human confirms the next step
  - browser-discovered field schemas and action sequences are preserved during setup; later flow discovery must not replace a richer executable action contract with a weaker selector-only action
- Voice defaults are female for both backend TTS and the browser greeting fallback. Backend TTS uses Azure Speech with `AZURE_SPEECH_TTS_VOICE` (default `en-IN-NeerjaNeural`) and `AZURE_SPEECH_TTS_STYLE` (default `empathetic`). The browser fallback picks the first matching name from the female-voice hint list in `plugin/src/audio/speech.js`, and reports failure so the widget can fall back to server TTS when no voice is available.

Important reality: this is a strong automatic foundation, not a magic 100% automation guarantee for every website on the internet. Public pages with readable HTML, standard forms/buttons, Shopify/WooCommerce hints, and accessible APIs work best. Login-only pages, CAPTCHA, payment steps, private APIs, anti-bot systems, and heavily custom SPAs still need validation, feeds, API access, or explicit client support.

## Public Topology

Current public-domain deployment:

```text
Public domain:   https://demo1.ergobite.com
Server IP:       157.245.3.230
AI Hub CRM:      https://demo1.ergobite.com/crm/
AI Hub API:      https://demo1.ergobite.com/
Client Panel:    https://demo1.ergobite.com/client_panel/<client_id>
```

Shared Nginx routing is owned by the host:

```text
/                         -> AI Hub Docker app on 127.0.0.1:3002
/client_panel/<client_id> -> AI Hub-served Client Panel bundle built from client-panel/
```

Demo websites can run on different domains. They should load the AI Hub install script from this public Hub domain.
Public route changes belong in the host Nginx config, not in this repo.

> **Known inconsistency:** `docker-compose.yml` still falls back to an older host
> (`http://143.198.5.97/aihub`) for `PUBLIC_API_URL`, `PUBLIC_STOREFRONT_ORIGIN`, and
> `CORS_ORIGINS` when those variables are unset. Always set `HUB_PUBLIC_URL`,
> `PUBLIC_API_URL`, and `CORS_ORIGINS` explicitly in `.env` for any real deployment
> so the stale default is never used.

## One-Line Install Contract

Universal script shown in AI Hub CRM:

```html
<script defer src="https://demo1.ergobite.com/install.js"></script>
```

Generic deployed form:

```html
<script defer src="https://hub.example.com/install.js"></script>
```

Local AI Hub form:

```html
<script defer src="http://127.0.0.1:5176/install.js"></script>
```

The installer loads the hosted adapter runtime first, then the widget. The browser runtime derives a stable site id from the installed website origin and, for localhost/IP path deployments, a safe path scope when needed. On first page load, the Hub auto-creates or updates the client as Available, binds the origin, detects the vertical, generates runtime config, and seeds prompts. Crawl and Setup run stay manual until an admin moves the site to Current and explicitly starts the action.

Advanced explicit-site override still exists for controlled migrations:

```html
<script defer src="https://hub.example.com/install.js?site=client_site_id" data-site-id="client_site_id"></script>
```

Local explicit-site examples for independent test websites:

```html
<script defer src="http://127.0.0.1:5176/install.js?site=ai_kart" data-site-id="ai_kart"></script>
<script defer src="http://127.0.0.1:5176/install.js?site=policy_website" data-site-id="policy_website"></script>
```

Normal clients should not paste separate hook blocks. Client-specific behavior belongs in Hub-owned runtime config, generated selectors/actions, platform adapters, prompts, and CRM controls.

## Automatic Onboarding Flow

```text
Client site
  pastes one script tag
    |
    v
/install.js
  loads /mayabot-adapter.js
  loads /mayabot.js
    |
    v
Browser adapter discovery
  reads safe page signals:
    title, URL, text sample, links, buttons, forms, platform hints
    hard-widget/provider hints for action policy
    |
    v
POST /v1/widget/register
  creates or updates Hub client
  classifies vertical
  generates routes/selectors/actions
  generates first-page barrier policy from browser hints
  saves adapter config
  seeds prompt profile
  leaves the client available with no crawl queued
    |
    v
Adapter runtime refresh
  reloads runtime config after registration
  observes same-tab SPA route changes and rediscover pages
  observes meaningful async DOM changes and rediscover late-loaded controls
  merges fresh observations with previous learned/admin state
  records privacy-safe click/form-submit metadata for adapter learning
  promotes high-confidence learned actions into runtime adapter config
    |
    v
CRM client workspace
  Overview, Readiness, Catalog/Knowledge, Crawl, Activity,
  Adapter, Prompt, Controls, plus vertical-specific tabs
```

## Adapter Meaning

In this project, an adapter is not code the client must write.

The adapter is the Hub-controlled execution layer that tells the widget how to operate on a client website:

- What vertical the site belongs to.
- Which routes look like shop, search, booking, quote, cart, checkout, contact, policy, or support pages.
- Which selectors map to visible buttons/forms.
- Which actions are allowed for the vertical.
- Which platform hints were detected, such as Shopify or WooCommerce.
- Which safe fallback behavior should be used when direct platform APIs are not available.
- Which fallback target resolver should recover stale selectors from visible page labels and form fields.
- Which accessible nested DOMs, such as open web components and same-origin embedded frames, can be searched by the universal adapter.
- Which custom controls, ARIA roles, and contenteditable fields are treated as actionable or fillable targets.
- Which user-like DOM events are dispatched when operating buttons, custom controls, fields, and forms.
- Which action execution attempts succeeded, failed, were blocked, or fell through to fallback stages.
- Which guarded DOM sequences can run for multi-step forms and flows.
- Which live action candidates and prompt ideas were inferred from the pasted script.
- Which high-confidence browser interactions were promoted into executable adapter actions.

The browser runtime lives in `plugin/src/adapter/` and is served as `/mayabot-adapter.js`.

The generated per-client runtime config is returned by:

```text
GET /v1/widget/config?site_id=<site_id>
GET /v1/admin/clients/<site_id>/adapter
```

The CRM Adapter tab shows the generated code/config so admins can inspect what the Hub decided.

## Vertical System

The vertical is the real runtime selector. It is not just a visual label.

Built-in verticals currently include:

```text
ecommerce
travel
insurance
finance_broker
healthcare
food
real_estate
education
automotive
legal_services
jobs_recruiting
events_ticketing
construction
generic
```

Vertical definitions live in:

```text
agent/verticals/
crm/src/verticals/
```

Each vertical defines entity labels, entity types, readiness checks, risk level, workspace tabs, and allowed action categories.

Key endpoints:

```text
GET   /v1/admin/verticals
GET   /v1/admin/verticals/{vertical_key}
PATCH /v1/admin/clients/{site_id}/vertical
```

## Prompts

Prompt profiles are stored per client. CRM can create drafts, publish versions, and review version history.

Key files:

```text
db/prompts.py                                    (facade -> db/prompting/prompt_profiles.py)
agent/prompts/
crm/src/views/client-workspace/tabs/PromptTab.tsx
```

Key endpoints:

```text
GET  /v1/admin/clients/{site_id}/prompt-profile
POST /v1/admin/clients/{site_id}/prompt-profile
POST /v1/admin/prompt-versions/{version_id}/publish
```

Prompt assembly is layered:

```text
platform policy
  + vertical prompt
  + client published prompt profile
  + runtime capabilities
  + retrieved product or knowledge context
  + rolling session summary
  + recent conversation context
```

High-risk verticals must stay conservative. The assistant must not diagnose, underwrite, approve, make legal conclusions, promise returns, promise eligibility, or invent live availability/price/terms.

Prompt engineering rule: the prompt must adapt from the current website's discovered schema and evidence. It must not hardcode Policy, AI-KART, travel, ecommerce, insurance, or any other demo-specific behavior. Maya should ask only for missing fields, reuse facts already supplied by the user, set `answer_scope` on every response, and keep hidden reasoning internal.

## RAG And Knowledge

Ecommerce product RAG still works through the existing product tables. The generic RAG foundation has been added for other domains.

Key files:

```text
db/knowledge.py          (facade -> db/knowledge_base/knowledge_items.py)
db/answer_cache.py       (facade -> db/cache/answer_cache.py)
db/session_memory.py     (facade -> db/runtime/session_memory.py)
agent/retrieval/generic_rag.py
agent/retrieval/product_rag.py
agent/prompts/generic.py
```

Key endpoints:

```text
GET /v1/knowledge?site_id=<site_id>
GET /v1/knowledge/by-ids?site_id=<site_id>&ids=<id,id>
GET /v1/admin/clients/{site_id}/knowledge
GET /v1/admin/clients/{site_id}/answer-cache
```

Current rule: keep ecommerce stable while generic knowledge, generic entity display, and dynamic DOM control are introduced gradually. Do not delete product tables, ecommerce prompt wrappers, Shopify/WooCommerce support, or legacy ecommerce widget fallbacks until runtime reports and tests prove the generic path has production parity.

Tenant/data rule: each client must read and write through its own tenant schema. Product, plan, service, review, knowledge, embedding, session, and cache data must not mix across clients. When a client's inventory or business records change, crawl/sync updates the tenant copy, bumps `tenant_data_versions`, and marks stale cached answers so RAG and Maya's replies follow the current website data.

## API Surface

Interactive docs are served at `/docs` (FastAPI/OpenAPI). Full route list by group:

**AI runtime** (public; widget-facing, origin-checked and rate-limited)

```text
POST      /v1/shop                     One assistant turn, JSON response
POST      /v1/shop/stream              One assistant turn, SSE event stream
WEBSOCKET /v1/ws/shop                  Persistent voice session (preferred transport)
WEBSOCKET /ws/chat                     Legacy bi-directional voice transport
```

**Widget serving and browser runtime** (public)

```text
GET  /install.js                       One-line installer
GET  /mayabot.js                       Widget bundle
GET  /mayabot-widget.js                Widget bundle alias
GET  /mayabot-adapter.js               Browser adapter runtime bundle
GET  /mayabot-frame                    Widget iframe host
POST /v1/widget/register               Browser discovery beacon / client bootstrap
GET  /v1/widget/config                 Generated per-client runtime config
GET  /v1/widget/status                 Widget enable/disable state
POST /v1/widget/action-event           Action execution telemetry
POST /v1/widget/action-report          Batched action outcome report
POST /v1/widget/interaction-event      Privacy-safe interaction learning
POST /v1/widget/policy-event           Barrier/policy block report
POST /v1/client-log                    Browser-side diagnostics
```

**Public catalog and knowledge** (public; used by widget overlays)

```text
GET  /v1/products                      GET /v1/products/by-ids
GET  /v1/products/{product_id}/variants
GET  /v1/categories                    GET /v1/catalog/status
GET  /v1/knowledge                     GET /v1/knowledge/by-ids
POST /v1/cart  /v1/cart/add  /v1/cart/update  /v1/cart/checkout
GET  /v1/cart/{cart_id}
POST /v1/catalog/crawler/run
```

**CRM admin** (all require the `x-crm-admin-token` header)

```text
GET   /v1/admin/overview               GET   /v1/admin/settings
PATCH /v1/admin/settings               GET   /v1/admin/installer
GET   /v1/admin/conversations          GET   /v1/admin/analytics
POST  /v1/admin/analytics/summary      GET   /v1/admin/provider-usage
POST  /v1/admin/provider-usage/check   GET   /v1/admin/verticals
GET   /v1/admin/verticals/{vertical_key}

GET/POST/DELETE  /v1/admin/clients[/{site_id}]
POST  /v1/admin/clients/{site_id}/activate
POST  /v1/admin/clients/{site_id}/available
PATCH /v1/admin/clients/{site_id}/status
PATCH /v1/admin/clients/{site_id}/vertical
PATCH /v1/admin/clients/{site_id}/token-limits
PATCH/DELETE /v1/admin/clients/{site_id}/panel-password

POST  /v1/admin/clients/{site_id}/crawl
POST  /v1/admin/clients/{site_id}/auto-integrate
POST  /v1/admin/clients/{site_id}/auto-integrate/cancel
POST  /v1/admin/clients/{site_id}/assistant-smoke-tests
GET   /v1/admin/clients/{site_id}/operation-status
GET/POST /v1/admin/scan/{site_id}
GET   /v1/admin/capabilities/{site_id}
GET   /v1/admin/crawl-report/{site_id}

GET   /v1/admin/clients/{site_id}/adapter
PATCH /v1/admin/clients/{site_id}/adapter/actions
POST  /v1/admin/clients/{site_id}/adapter/action-candidates/review
POST  /v1/admin/clients/{site_id}/adapter/action-proposals/refresh
POST  /v1/admin/clients/{site_id}/adapter/action-proposals/review
POST  /v1/admin/clients/{site_id}/adapter/flow-repair-proposals/review

GET   /v1/admin/clients/{site_id}/flows
POST  /v1/admin/clients/{site_id}/flows/discover
GET   /v1/admin/clients/{site_id}/flows/regression
GET   /v1/admin/clients/{site_id}/flows/rehearsal
POST  /v1/admin/clients/{site_id}/flows/rehearse

GET/POST /v1/admin/clients/{site_id}/prompt-profile
POST  /v1/admin/prompt-versions/{version_id}/publish
GET   /v1/admin/clients/{site_id}/knowledge
GET   /v1/admin/clients/{site_id}/answer-cache
GET   /v1/admin/clients/{site_id}/isolation-audit
```

**Client Panel** (bearer token issued by `/login`, HMAC-signed, expires, and is
invalidated when the panel password is rotated or revoked)

```text
POST  /v1/client-panel/login
GET   /v1/client-panel/me
GET   /v1/client-panel/dashboard
PATCH /v1/client-panel/token-policy
```

**Utility**

```text
GET /health                            Includes provider_status since 2026-07-16
```

## Repository Layout

```text
agent/            AI orchestration, prompts, RAG, crawler, verticals, actions, adapters
api/              FastAPI app shell, route modules, CRM APIs, Client Panel APIs, widget serving
crm/              React 19 / Vite 8 CRM frontend (admin)
client-panel/     React 19 / Vite 8 Client Panel frontend (customer-facing analytics)
db/               Admin facade, schema, clients, prompts, knowledge, quota, analytics
plugin/           Hosted browser widget and adapter runtime source (esbuild IIFE bundles)
packages/         Shared JS/TS action contracts consumed by crm/ and plugin/
tests/            Backend, ingestion, guardrail, vertical, knowledge, and widget tests
scripts/          Contract drift checker and persona runners
data/             Local development data and fixtures
docker/           Container entrypoint
.github/          CI workflow
```

Compatibility rule:

```text
Existing imports from db.admin should keep working.
Public API paths should stay stable.
AI-KART must keep working without AI Hub.
```

The repository uses a **facade module** convention to keep those import paths stable
while the implementation is split into smaller files:

- Python facades (`agent/orchestrator.py`, `api/main.py`, `db/admin.py`, and ~22 more)
  rebind `sys.modules[__name__]` to the real implementation module.
- TypeScript/JavaScript facades (`crm/src/App.tsx`, `plugin/src/widget.js`, and ~60 more)
  are one-line `export * from './real/path'` re-exports.

Import the facade path when you want the stable public name; import the implementation
path when you need a specific symbol. Grep for both when tracing code.

## Local Development

Use this when you want the full Hub exactly like deployment:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose up -d --build
```

Open:

```text
http://127.0.0.1:5176/health
http://127.0.0.1:5176/crm/
```

Use this when you want backend hot reload from local Python:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose up -d db

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
playwright install chromium

uvicorn api.main:app --reload --host 127.0.0.1 --port 8585
```

Build AI Hub frontend bundles:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
corepack pnpm install
corepack pnpm --filter ai-hub-crm build
```

Build widget and adapter bundles:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
corepack pnpm --filter mayabot-plugin build
```

If you see `ModuleNotFoundError: No module named 'app'`, you are probably running an AI-KART command in the Hub repo, or a Hub command in the AI-KART repo. AI Hub runs with:

```powershell
uvicorn api.main:app --reload --host 127.0.0.1 --port 8585
```

AI-KART runs separately from `C:\Users\admin\Desktop\Vercel_website\backend` with:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Environment

Root `.env` belongs to AI Hub only.

Do not put AI-KART website admin credentials here. AI-KART admin credentials belong in:

```text
C:\Users\admin\Desktop\Vercel_website\backend\.env
```

Local DB default:

```env
DATABASE_URL=postgresql://shopbot:shopbot_password@localhost:5434/shopping_db
```

Server Docker DB default:

```env
DATABASE_URL=postgresql://shopbot:shopbot_password@db:5432/shopping_db
```

Important Hub environment keys:

```env
# Public identity and CORS
HUB_PUBLIC_URL=https://demo1.ergobite.com
PUBLIC_API_URL=https://demo1.ergobite.com
CORS_ORIGINS=https://demo1.ergobite.com
DEPLOYMENT_MODE=production

# Credentials (all three are required; the app refuses admin/panel auth without them)
CRM_ADMIN_TOKEN=                      # min 12 chars, else CRM admin API returns 503
CLIENT_PANEL_TOKEN_SECRET=            # HMAC signing key; min 16 chars, else login 503s
CLIENT_PANEL_DEFAULT_PASSWORD=        # fallback only; min 12 chars or new clients get none

# Azure AI Services: one endpoint/key for chat, STT, and TTS
AZURE_SPEECH_ENDPOINT=https://your-resource.cognitiveservices.azure.com
AZURE_SPEECH_KEY=
AZURE_RESOURCE_ID=/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/your-resource
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_REASONING_EFFORT=none
AZURE_OPENAI_TIMEOUT_SECONDS=30
AZURE_SPEECH_TTS_VOICE=en-IN-NeerjaNeural
AZURE_SPEECH_TTS_STYLE=empathetic
AZURE_SPEECH_TIMEOUT_SECONDS=30

# Cost and payload ceilings
LLM_MAX_TOKENS=320
LLM_MAX_TOKENS_HARD_CAP=320           # LLM_MAX_TOKENS is clamped to this
TTS_CHUNK_CHARS=1200
TTS_MAX_INPUT_CHARS=12000
MAX_AUDIO_UPLOAD_BYTES=10485760

# Crawl and startup behaviour
CRAWL_ON_STARTUP=false
CRAWL_PERIODIC_ENABLED=false
ENSURE_DEFAULT_CLIENT_ON_STARTUP=false
CLEAN_SYNTHETIC_DEMO_CLIENTS_ON_STARTUP=true
CRAWL_MAX_PAGES=60
CRAWL_MAX_DEPTH=3
SETUP_RUN_TIMEOUT_SECONDS=7200

# Operational
TRUSTED_PROXY_IPS=                    # comma-separated IPs or CIDRs; required behind Nginx
                                      # so per-IP rate limiting sees the real client IP
LOG_CONVERSATION_CONTENT=false        # keep false in production; true logs transcripts
CLIENT_TLS_VERIFY=true
RAG_TOP_K=10
RAG_TOP_N=50
ACTION_AUTO_APPROVE_CONFIDENCE=0.75
```

`CURRENT_SITE_ID`, `DEFAULT_SITE_ID`, `AI_DEFAULT_SITE_ID`, `CLIENT_STORE_URL`, `PUBLIC_STOREFRONT_ORIGIN`, and `CURRENT_URL` are client/demo-site settings. Do not set them for a Hub-only deployment unless you intentionally want a fixed fallback client or startup crawler target.

## Deployment

Use:

```text
docs/deployment.md
```

> **Note:** `docs/` and `deploy/` are currently listed in `.gitignore`, so
> `docs/deployment.md` and `deploy/nginx.conf` exist on the maintainer's machine but
> are **not** in the repository. A fresh clone has no deployment runbook and no Nginx
> reference config. Either remove those `.gitignore` entries and commit the files, or
> move the runbook into a tracked location.

High-level order:

1. Deploy AI Hub from `/var/www/AI_salesman_plugin/docs/deployment.md`.
2. Deploy or reload the host Nginx config.
3. Build the Docker app; it compiles CRM and Client Panel from this repository.
4. Open CRM and confirm the client workspace, Setup workspace, adapter tab, prompt tab, client-panel link, and crawl status.

Production AI Hub runs in Docker Compose:

```text
db  -> PostgreSQL with pgvector
app -> FastAPI app, CRM static files, widget bundle, AI pipeline
```

AI Hub serves the client-facing analytics panel from `client-panel/dist` in this
repository. Override `CLIENT_PANEL_SOURCE_DIR` or `CLIENT_PANEL_STATIC_DIR` only
when intentionally serving a separately built bundle.

AI Hub production does not use a host Python venv for runtime.

## Testing

Backend:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
python -m pytest -q
python -m compileall agent api db tests
```

CRM:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
corepack pnpm --filter ai-hub-crm build
```

Client Panel:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
$env:VITE_CLIENT_PANEL_BASE_PATH="/client_panel/"
$env:VITE_AI_HUB_API_BASE=""
corepack pnpm --filter client-panel build
```

Widget:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
corepack pnpm --filter mayabot-plugin build
```

Useful focused tests:

```powershell
python -m pytest tests/test_vertical_registry.py tests/test_vertical_prompt_runtime.py -q
python -m pytest tests/test_widget_install_scripts.py tests/test_widget_registration.py -q
python -m pytest tests/test_flow_discovery.py tests/test_flow_rehearsal.py tests/test_flow_barriers.py -q
python -m pytest tests/test_knowledge.py -q
python -m pytest tests/test_runtime_security.py tests/test_input_guardrails.py tests/test_output_guardrails.py -q
python -m pytest tests/test_orchestrator_product_matching.py tests/test_orchestrator_action_truth.py -q
```

Integration tests that need a live PostgreSQL are marked, so they can be excluded:

```powershell
python -m pytest -q -m "not integration"
```

Run the whole CI pipeline locally (the same sequence `.github/workflows/ci.yml` runs):

```powershell
corepack pnpm run ci
```

Manual no-bias local onboarding test:

Use the command block in "Local Independent Manual Test" below. Start both client
websites independently, start AI Hub independently, then paste each CRM-generated
script into that website's `index.html`. Keep the local Hub database persistent
while testing; only disable automatic default-client seeding to avoid hidden bias.
Clients created by the script remain in that database until deleted from CRM.

Verification history:

```text
2026-07-29 (current)  python -m pytest -q            -> 643 passed, 1 skipped
2026-07-16            python -m pytest -q            -> 488 passed, 1 skipped
earlier               python -m pytest -q            -> 459 passed
```

Full check on 2026-07-29:

```text
python -m pytest -q                           -> 643 passed, 1 skipped in 276s
python -m compileall agent api db tests        -> passed
corepack pnpm run contracts:check              -> 73 actions matched
corepack pnpm --filter ai-hub-crm lint         -> clean
corepack pnpm --filter client-panel lint       -> clean
corepack pnpm -r run build                     -> contracts, client-panel, crm, plugin all built
```

### Continuous Integration

`.github/workflows/ci.yml` runs on every pull request and on pushes to `main`. It
starts a `pgvector/pgvector:pg16` service and then runs, in order:

```text
python -m pip check
pnpm run contracts:check
pnpm --filter ai-hub-crm lint
pnpm --filter client-panel lint
pnpm -r run build
python -m compileall agent api db tests
python -m pytest -q
```

There is currently **no frontend test runner** (no vitest/jest/Playwright config in
`crm/`, `client-panel/`, or `plugin/`). Browser behaviour is covered indirectly from
the Python side by tests such as `tests/test_browser_runtime_action_execution.py`
and `tests/test_browser_universal_form_flow.py`, which drive the built bundles.

## Operational Boundaries

AI Hub owns:

- Widget serving.
- Hosted adapter runtime.
- CRM and admin APIs.
- Client Panel APIs.
- Conversation logs and analytics.
- Crawled/vectorized copies of client data.
- Prompt profiles.
- Vertical definitions.
- Generated adapter configuration.

AI Hub does not own:

- Client website source code.
- Client user accounts.
- Client checkout, booking, payment, claim, quote, or application finalization.
- AI-KART website admin credentials.
- Public root Nginx routing.

## Reliability Roadmap

Current automatic-discovery reliability layer:

- Server-side Playwright flow discovery with HTTP fallback.
- Safe flow rehearsal with browser verification and HTTP/static fallback.
- Hard-flow barrier detection for auth gates, CAPTCHA, iframes, payment handoffs, calendars, maps, file uploads, and external action links.
- Barrier-aware action policy that blocks unsafe finalization actions and exposes handoff actions in prompts, CRM, and runtime config.
- Widget runtime stops unsafe fallback execution after a policy block and shows a visible handoff panel for checkout, agent, advisor, clinic, legal, recruiting, and generic human handoff actions.
- Contract-aware output guardrails that allow generated adapter routes/actions while sanitizing dynamic form and sequence params.
- Flow regression detection when routes, actions, or rehearsed targets change between scans.
- Browser-side dry-run validation of generated selectors/actions from the pasted script.
- Browser-side live page context is sent with each HTTP/WebSocket turn so prompts see current path, actions, routes, buttons, links, and form fields.
- Browser-side target resolution fallback for stale click/form/sequence selectors.
- Browser-side deep DOM traversal for open shadow roots and same-origin iframes.
- Browser-side custom-control coverage for ARIA/menu/tab/combobox/searchbox/contenteditable widgets.
- Browser-side event driver for pointer, mouse, keyboard, text-entry, select, checkbox, and submit behavior.
- Browser-side generic form filler that maps action parameters to fields by label, name, placeholder, autocomplete, select options, checkbox, and radio metadata.
- Browser-side action execution telemetry for repair and admin review.
- Runtime action-health loop that turns repeated browser execution failures into CRM repair warnings and temporary runtime policy blocks.
- Runtime self-repair bridge that can replace broken generated actions from high-confidence recent browser interactions while preserving CRM overrides.
- Flow-level repair proposals that group route/action drift into CRM-reviewable patch plans after regression checks.
- Optional LLM-assisted flow repair proposals, validated into safe same-origin route/action patches before CRM review.
- Modular widget action executor that delegates platform actions to the shared universal adapter layer.
- Modular generic entity executor and overlay for source-backed non-commerce knowledge results.
- Browser-side hard-widget/provider detection during first registration.
- Browser-side safe provider handoff openers for map, appointment scheduler, and contact-provider URLs.
- Provider-specific handoff playbooks for login/CAPTCHA, payment, calendar, file upload, iframe, and external-provider boundaries.
- Browser-side async DOM rediscovery for hydrated buttons, forms, iframes, and fields.
- Rediscovery-safe persistence that preserves learned/admin runtime state across repeated registrations.
- Browser-side interaction learning from observed clicks and form submits, without storing typed field values.
- Vertical-aware learned action promotion with manual override protection.
- Vertical-aware sales intake prompt block that makes the assistant collect missing domain facts before quote, booking, checkout, application, appointment, or lead-capture actions.
- Runtime action-readiness prompt block that names missing required params and follow-up questions before generated actions are emitted.
- Runtime sales-relevance scope that keeps Maya focused on buying, comparison, product/service facts, and safe website actions.
- Tenant-local answer cache for repeated grounded questions, with side-effect action bypasses and data-version invalidation.
- Bounded session memory that combines a compact summary with recent turns instead of sending an unbounded transcript.
- CRM approve/reject workflow for live action candidates.
- CRM refresh/approve/reject workflow for action repair proposals.
- CRM approve/reject workflow for flow-level route/action repair plans.
- Tenant/RAG/cache isolation audit for per-client runtime, prompt, install, knowledge, embedding, and answer-cache boundaries.
- Robots/sitemap-aware HTTP discovery fallback.
- Static cleanup guards against old monolithic widget action files, demo-site globals, and hardcoded AI-KART/ecommerce widget chrome.
- Provider-heavy fixture coverage for travel, healthcare, insurance, ecommerce, construction, education, and recruiting layouts with handoff playbooks and prompt-safe browser context.
- Confidence scores per route/action.
- CRM override editor for adapter config.
- CRM flow rehearsal controls and confirmation policy visibility.
- CRM automation-barrier visibility with handling guidance.
- CRM site-change visibility for broken or changed routes/actions.
- Flow-generated prompt suggestions visible in CRM.
- Setup-run assistant smoke tests that run source-backed prompts through Maya and flag missing expected UI actions or no-record fallback responses.
- Universal domain readiness matrix for every built-in vertical, covering discovery-profile action compatibility, deterministic setup-smoke actions, and source-backed non-commerce fact-answer recovery.
- Browser runtime action-execution regression proving generated form/sequence actions returned by Maya can be executed by the hosted adapter and navigate the website.
- Universal safe-submit action contracts: generated quote/search/availability/calculator forms can submit only when the detected fields and labels show a low-sensitivity results flow; sensitive lead/application/payment/booking/claim forms remain prepare-only or handoff-first.
- Setup merge protection for executable form contracts: browser-discovered field schemas, required params, submit mode, and DOM sequences are not overwritten by weaker later flow observations.

Remaining reliability work before claiming near-universal autonomous control:

- Real-world provider-specific control/repair tuning for auth walls, complex iframe widgets, payment pages, and CAPTCHA handoff flows.
- Real-world tuning of LLM-assisted flow repair across complex live layouts.
- Live browser testing against real deployed third-party layouts per vertical, not only deterministic fixture pages.
- Deeper provider-specific integrations for payment, login, regulated decisions, CAPTCHA, and uncertain external widgets.

Until those remaining layers exist, the system should be presented as automatic discovery plus admin-verifiable setup, not as guaranteed perfect autonomous control on every site.

## Known Issues

A full code review of the backend, both frontends, and the browser plugin lives in
`review.md`. Confirmed defects worth knowing before you deploy:

- The security middleware applies CSP and `X-Frame-Options` to `/client-panel` (the
  legacy path) but not `/client_panel` (the path actually served to customers), so the
  live Client Panel ships without those headers.
- `config.VALID_UI_ACTIONS` is a third, unchecked copy of the action list and has
  already drifted from `agent/actions/registry.py` by four construction-vertical
  actions. `scripts/check_contracts.py` only compares the registry against the
  TypeScript contracts, so it cannot catch this.
- `agent/orchestration/orchestrator_pipeline.py` branches on `PYTEST_CURRENT_TEST`
  in three places, so the production pipeline behaves differently under test than in
  production.
- `.env.example` sets `RAG_TOP_N=3` while `config.py` defaults to `50`.

## Troubleshooting

`/health` fails publicly but `127.0.0.1:3002/health` works:

```text
Shared Nginx route is missing or stale. Apply Vercel_website/aikart.md.
```

CRM shows old assets:

```text
Rebuild the Docker app using `docs/deployment.md`, then hard refresh the browser.
```

Client Panel login fails:

```text
Check CLIENT_PANEL_TOKEN_SECRET in AI Hub .env and set or generate the client's panel password from CRM.
The CRM admin token and client-panel password are separate credentials.
```

AI-KART admin login fails:

```text
Do not change AI Hub .env. AI-KART admin credentials live in Vercel_website/backend/.env.
```

Widget appears but microphone recording fails on public HTTP:

```text
Production microphone access needs HTTPS. DNS plus HTTPS is required for reliable public mic support.
```

## Local Independent Manual Test

Use separate terminals. Start AI Hub first, then the independent test websites.

AI Hub Docker app and database:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose up -d --build
```

Open CRM:

```text
http://127.0.0.1:5176/crm/
```

Stop AI Hub later:

```powershell
cd C:\Users\admin\Desktop\AI_salesman_plugin
docker compose stop
```

AI-KART backend:

```powershell
cd C:\Users\admin\Desktop\Vercel_website\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

AI-KART frontend:

```powershell
cd C:\Users\admin\Desktop\Vercel_website\frontend
npm run dev -- --host 0.0.0.0 --port 5175
```

Policy backend:

```powershell
cd C:\Users\admin\Desktop\Policy_website\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8003
```

Policy frontend:

```powershell
cd C:\Users\admin\Desktop\Policy_website\frontend
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:8003"
npm run dev -- --host 0.0.0.0 --port 5183
```

Open test websites:

```text
AI-KART: http://127.0.0.1:5175/
Policy:  http://127.0.0.1:5183/
```

Client panel links are hosted by AI Hub, for example:

```text
http://127.0.0.1:5176/client_panel/site_1
http://127.0.0.1:5176/client_panel/site_2
```

`CLIENT_PANEL_DEFAULT_PASSWORD` is only a fallback for clients that do not already
have a stored panel password. For existing clients, use CRM -> Client -> Manage
password before sharing the panel URL. If the fallback is shorter than 12
characters, new clients are left with no configured panel password so CRM must
generate or set one before the panel can be shared.

Current local script tags:

```html
<script defer src="http://127.0.0.1:5176/install.js?site=ai_kart" data-site-id="ai_kart"></script>
<script defer src="http://127.0.0.1:5176/install.js?site=policy_website" data-site-id="policy_website"></script>
```

Expected manual flow:

```text
1. Open each test website once so the script registers the site.
2. CRM shows the install under Available, grouped as Online or Offline by reachability.
3. Move the install to Current.
4. Run setup only when the source website is online.
5. Setup produces crawl, flow, readiness evidence, and prompt smoke-test evidence.
6. Crawl stays locked while the source website is offline.
```

Production customer persistence:

```text
ENSURE_DEFAULT_CLIENT_ON_STARTUP=false only disables implicit default-client seeding.
It does not make clients temporary. Customers remain permanent as long as the same
database volume is used and the client is not deleted from CRM.
```
