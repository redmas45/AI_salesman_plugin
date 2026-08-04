# Global Engineering Standard: Professional Code Quality & Architecture Guidelines

This document outlines the expanded, world-class engineering standards required for building scalable, maintainable, and production-grade software ecosystems. These rules govern all codebases, from frontend applications and backend APIs to automated pipelines and data processing engines.

---

## 1. Name Elements for 2 AM Readability (Intent Over Brevity)
Names must clearly communicate intent, context, and responsibility. Code is read significantly more often than it is written; avoid clever shortcuts, non-standard abbreviations, or ambiguous single-letter variables.

* **Variable Names:** Use descriptive nouns that reflect the exact data held.
    * *Bad:* `t`, `c_list`, `f_data`
    * *Good:* `elapsed_time_seconds`, `active_claims_list`, `processed_frame_data`
* **Function/Method Names:** Use strong action verbs that explicitly describe the operation.
    * *Bad:* `proc()`, `handle_doc()`, `calculate()`
    * *Good:* `process_incoming_fnol_submission()`, `extract_ocr_document_metadata()`, `calculate_sla_compliance_rate()`
* **Class Names:** Use clear nouns or noun phrases representing an entity, component, or conceptual domain.
    * *Good:* `ClaimsWorkflowAutomationEngine`, `DigitalWalletPassGenerator`, `StripeLedgerReconciliationService`

## 2. Single Responsibility Principle (One Function, One Job)
A function or class should have one, and only one, reason to change. If your explanation of a function requires the word "and", it is a candidate for decomposition.

* **Atomic Operations:** Break complex logic into tightly focused, re-usable functions that perform a single operational primitive.
* **Integration vs. Action:** Separate functions that orchestrate workflow steps from functions that perform the actual processing/computation.
* **Maintainability Impact:** Isolating tasks simplifies writing comprehensive unit tests, accelerates debugging, and decreases the blast radius of structural changes.

## 3. Total Elimination of Magic Numbers and Literals
Hardcoded literals (strings, integers, floats) introduce fragile dependencies, hinder global refactoring, and obscure business rationale.

* **Named Constants:** Every literal that possesses semantic weight must be declared as a named constant or structured enum.
* **Centralized Configuration:** Infrastructure values (timeouts, retry limits, file size caps) belong in config environments or strict registry objects.
* **Example Implementation:**
    * *Bad:* `if (claim.amount > 500) { route_to_handler(); }`
    * *Good:* `if (claim.amount > MAX_AUTO_APPROVE_CLAIM_VALUE_GBP) { route_to_handler(); }`

## 4. Explicit and Defensive Error Handling
Production software must fail gracefully, predictably, and informatively. Swallowing errors or assuming happy-path execution is strictly forbidden.

* **Specific Exception Handling:** Never catch generic top-level exceptions (e.g., raw `Exception` or `Error`) unless logging and re-throwing. Catch exact operational exceptions (e.g., `TimeoutError`, `ValidationError`).
* **Clean Failure States:** Ensure database connections, open file handles, and stream resources are guaranteed to close using transactional boundaries or resource managers (`try-catch-finally`, `with` blocks).
* **Sufficient Auditing:** Log exceptions with complete context (transaction IDs, error stack traces, payload snapshots) while sanitizing sensitive user data or PII. Surface clean, actionable, non-technical messages to end users.

## 5. Elimination of Unintended Side Effects (Pure Functions)
State mutations hidden within standard functions create unpredictable runtime tracking, complex race conditions, and difficult-to-reproduce bugs.

* **Immutability by Default:** Functions should treat input arguments as read-only. Avoid modifying arrays, objects, or data models passed by reference.
* **Explicit State Changes:** If a function must mutate state or interact with the external environment (I/O, databases, file systems), clearly isolate it or structure it as an explicit state-transition method within an orchestrator class.
* **Data Integrity:** Return a newly constructed data model or payload instead of modifying existing data structures.

## 6. Comprehensive Strict Typing & Schema Enforcement
Type definitions act as a compile-time firewall against runtime exceptions and form a living, machine-enforced documentation layer.

* **Signature Completeness:** Every function must explicitly annotate all argument types and the exact return type.
* **No Dynamic Escapes:** Avoid structural fallback types (like Python's `Any` or TypeScript's `any`) unless dealing with un-parsed wire protocols at an input boundary.
* **Data Model Validation:** Enforce strict runtime data schemas (using tools like Pydantic, TypeScript interfaces, or Mongoose schemas) at all persistence and ingestion layers.

## 7. Informative Comments (Documenting the "Why", Not the "What")
Code explains the mechanism; comments must explain the underlying business intent, architectural constraints, or mathematical rationale.

* **Code Self-Documentation:** If the code is complex, refactor the naming, structure, or abstractions to make it legible before writing a descriptive comment.
* **Strategic Explanations:** Use comments exclusively to justify non-obvious engineering decisions, edge-case fixes, upstream architectural limitations, or complex business logic overrides.
* **Drift Prevention:** Outdated comments are more dangerous than no comments. Ensure comments are updated in lockstep during every refactoring phase.

## 8. Flat and Compact Call Stacks (Early Returns & Micro-Functions)
Deeply nested, expansive functions tax cognitive load and obscure logical exit paths. Aim to keep code readable from top to bottom.

* **Physical Size Limits:** Strive to keep functions within 30 lines of execution logic. If a function stretches beyond a screen-height, abstract its internal sub-blocks.
* **Guard Clauses & Early Returns:** Eliminate cascading `if-else` pyramids by immediately checking preconditions and returning or throwing errors early.
* **Cyclomatic Complexity Cap:** Maintain a maximum nesting depth of 2 levels. Use loop-extraction techniques or functional map/filter operations to keep blocks flat.

## 9. Zero-Trust Ingestion (Rigorous Boundary Validation)
All data crossing an architectural boundary (API endpoints, webhook targets, public methods, uploaded files, configuration strings) must be treated as hostile and untrusted.

* **Sanitization and Typing:** Validate structure, types, constraints, ranges, and characters immediately upon arrival at the boundary layer.
* **Structural Defensiveness:** Reject invalid payloads immediately at the perimeter before allowing data to traverse downstream to application logic or storage tiers.
* **Fail-Fast Architecture:** Catching anomalies early prevents corrupt database tracking, injection vulnerabilities, and deep-stack processing crashes.

## 10. Intentional Abstraction (The Rule of Three)
Premature abstraction is a leading driver of bloated, rigid, and over-engineered architectures. Write code for clarity today, and abstract for reuse tomorrow.

* **Duplicate Twice:** Copying and pasting code or logic exactly twice is perfectly acceptable if it preserves clear separation between two separate business domains.
* **Abstract on the Third Recurrence:** Only when a pattern or logical block emerges for the *third* time should you design and implement a generalized abstraction, helper module, or shared utility interface.
* **Domain Preservation:** Ensure you are abstracting shared *structural realities*, not coincidental similarities that happen to look alike today but will evolve in entirely different directions tomorrow.

## 11. Modular Architecture, Classes, and File Size Budgets
Large files hide design flaws, slow review, and make demo-critical changes risky. A production module must have an explicit ownership boundary and should not become a dumping ground for unrelated workflows.

* **File Size Budget:** Keep source files under 500 lines by default. A file may grow to roughly 800 lines when the extra length genuinely belongs to one cohesive domain, or when it is a deliberate registry, generated artifact, schema, migration, or dense test fixture. **1000 lines is the hard maximum.** Any file approaching that ceiling must be refactored into domain modules before new feature work is added to it.
* **Class Boundaries for Stateful Domains:** Use classes for cohesive domain services that own state, dependencies, or policy, such as orchestration engines, response grounders, retrieval services, adapter scanners, and setup planners. Constructor dependencies should make external collaborators explicit.
* **Pure Helpers Stay Small:** Do not force OOP where a stateless pure function is clearer. Pure parsing, formatting, validation, and scoring helpers are acceptable when they are short, typed, side-effect free, and grouped in a focused module.
* **Orchestrator Thinness:** Orchestrators should coordinate workflow steps, not contain all business logic. Move retrieval ranking, product formatting, action repair, cache policy, prompt assembly, and browser action grounding into separately testable services.
* **No Mega-Modules:** If a module contains multiple unrelated sections, split by domain capability instead of by technical convenience. Example: product response grounding belongs in a product response service, not in a voice pipeline orchestrator.
* **Performance Reality:** Classes and objects do not automatically make software faster or more memory efficient. Performance comes from bounded data structures, avoiding repeated I/O, avoiding unnecessary copies, lazy loading expensive dependencies, and using clear ownership so caches and resources are managed intentionally.

## 12. Plan, Review, and Git Control

* **Read Before Editing:** Read `AGENTS.md`, this file, `handoff.md`, relevant manifests, tests, and nearby implementation before changing code.
* **Approved Scope Only:** Follow the reviewed plan. Record material scope discoveries in `handoff.md` and obtain approval before expanding the task.
* **No Delivery Actions:** Delegated workers must not commit, push, create or switch branches, open pull requests, tag releases, or deploy. They leave local working-tree changes for independent review; the user performs Git and deployment actions manually after a green signal.
* **Preserve Existing Work:** Never reset, clean, stage, rewrite, or remove unrelated working-tree changes. Work with concurrent changes when they affect the task.

## 13. Repository Ownership and Vertical Independence

* **Hub Ownership:** `AI_salesman_plugin` owns universal ingestion, normalization, retrieval, prompts, memory, cache, voice runtime, CRM, adapters, and cross-vertical behavior.
* **Demo Website Ownership:** `Vercel_website` owns AI-KART catalog truth, product API, media, storefront behavior, responsive UI, and source-catalog validation.
* **Fix the Owning Boundary:** Do not hide malformed website data with tenant-specific Hub code. Do not make Hub correctness depend on every connected website being perfectly curated.
* **No Production Fixture Rules:** AI-KART names and screenshot transcripts may appear in tests, but production logic must use typed domain fields and vertical contracts rather than hardcoded demo names.
* **Separate Review:** Keep Hub and AI-KART changes independently reviewable and verify each repository with its own toolchain.

## 14. Deterministic Retrieval and Dialogue Contracts

* **Parse Before Retrieval:** Resolve domain intent, entity/brand, item or service type, budget/range, recipient, occasion, requested attributes, exclusions, ambiguity, and references before candidate ranking.
* **Hard Constraints Are Authoritative:** Explicit brand, type, price, availability, exclusion, and ownership constraints use field-aware conjunctive checks. Semantic similarity and LLM output cannot override them.
* **Candidate Generation Is Not Approval:** Lexical, semantic, fuzzy, cached, and history-derived candidates pass through one deterministic validator before they can be mentioned or actioned.
* **Clarify Real Ambiguity:** Low-confidence, malformed, recipient-only, or genuinely underspecified requests get one useful clarification instead of arbitrary recommendations.
* **Ground Every Record:** Every product, plan, destination, service, or other entity named in a response or UI action must belong to the final validated candidate set.
* **Use Precise Counts:** Distinguish matching records, variants, and stock units. Never claim whole-catalog truth from a retrieval window.
* **Topic-Aware Memory:** Preserve explicit references while resetting stale constraints when the user changes subject or corrects the assistant.
* **Constraint-Safe Cache:** Cache identity includes site/tenant, data version, session scope, normalized intent, and hard constraints. Cached and uncached behavior must remain semantically equivalent.
* **Prompt Is Not Enforcement:** Prompt changes may improve style and interpretation but never replace runtime validation for budgets, identity, category, stock, actions, or grounding.

## 15. Voice, Conversation UI, and Accessibility

* **Single Playback Owner:** One controller owns generated audio, browser speech, playback queues, cancellation, object cleanup, and speaking state.
* **Immediate Interruption:** Orb click while speaking, a visible stop control, and `Escape` must stop active and queued audio without accidentally starting recording.
* **Copy Controls:** Conversation and message copy actions use familiar icons, accessible labels, keyboard operation, and explicit success/failure feedback.
* **Responsive Verification:** Check affected interfaces at 320, 375, 390, 768, 1024, 1440, and 1920 CSS pixels plus 200% zoom. Text and controls must not overlap or become unreachable.

## 16. Performance and Latency Evidence

* **Measure Before Optimizing:** Record cold/warm state, cache state, sample count, environment, and p50/p95 for cache, retrieval, LLM, TTS, first text, first audio, and total time.
* **Use Staged Work:** Prefer deterministic structured fast paths. Run semantic, fuzzy, LLM, or provider work only when it can improve the result.
* **Correctness Before Speed:** Never lower validation thresholds, omit hard checks, replay unsafe cache entries, or return ungrounded partial answers to improve latency.
* **Comparable Results Only:** Do not compare unlike local/public, cold/warm, cached/uncached, or provider environments without labeling the difference.

## 17. Regression and Cross-Vertical Verification

* **Reproduce First:** Add a failing regression test for each reported defect before implementing its fix.
* **Cover Failure Modes:** Test ambiguity, correction, no-match, stale context, cache parity, provider failure, accessibility, cancellation, and latency in addition to happy paths.
* **Generalization Evidence:** Use exact reported transcripts for regressions and neutral variants for generalization. Shared changes must also pass travel and policy fixtures.
* **Layered Verification:** Run focused tests while editing, followed by relevant Python, frontend, catalog, lint, build, integration, and browser checks.
* **Report Honestly:** A timed-out, skipped, unavailable, flaky, or unrun check is not a pass. Record its exact state in `handoff.md`.

## 18. Delegated Worker Handoff

* **Maintain the Journal:** Update the ignored `handoff.md` throughout implementation, not only at completion.
* **Record Reviewable Rationale:** Log concise decisions, alternatives, evidence, changed files, commands, results, timings, assumptions, blockers, and remaining risks.
* **Protect Sensitive Reasoning and Data:** Do not record private chain-of-thought, hidden reasoning, secrets, `.env` values, credentials, raw audio, customer PII, or unrestricted provider payloads.
* **Stop for Review:** Finish with separate working-tree summaries for each repository and a complete verification ledger, then stop for independent review without any Git or deployment action.
