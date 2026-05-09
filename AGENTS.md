# AGENTS.override.md — Sales Trainer

> Scope: repository root. This file is intended to override/extend any broader Codex instructions for this project.
> Codex loads project instructions from repository root down to the working directory; closer nested instruction files override broader ones.
> Keep it concise enough to fit Codex project-instruction limits. If it grows too large, split specialized rules into nested `AGENTS.override.md` files.

## 0. Non-negotiable operating rules

1. Work as a careful coding agent, not as a code generator dumping patches.
2. Before changing code, understand the touched flow end-to-end: domain model → application service → infrastructure/API/CLI/frontend → tests.
3. Preserve the product invariant: the application owns canonical state; the LLM only simulates the next client turn and proposes bounded patches.
4. Never expose hidden client/persona data to the trainee-facing API, frontend, public logs, browser state, or normal CLI output.
5. Never commit secrets, API keys, cookies, tokens, database dumps, `.env`, local credentials, or raw LLM payloads containing sensitive data.
6. Do not silently degrade production/staging behavior to fake LLM or in-memory repository.
7. Do not rewrite architecture for convenience. Make small, isolated, reviewable changes.
8. Before editing, inspect current repository state; never overwrite user work, unrelated changes, or uncommitted files you did not create.
9. Do not commit, push, rebase, reset, amend, or create PRs unless the user explicitly asks for that action.
10. Every behavior change must have tests or an explicit, honest reason why it could not be tested.
11. Never claim tests passed unless you actually ran them and saw a successful result.
12. After every completed iteration, update this file’s **Current state**, **Backlog**, and **Rules changelog** sections before finalizing the work.

## 1. Project identity

**Product:** Sales Trainer MVP — interactive B2B sales training simulator.

A manager writes messages to a simulated cold B2B client. The system replies as a hidden decision-maker/contact, updates interest and conversation state, and produces a training report.

**Core product idea:**

- The LLM is stateless.
- The backend owns session state.
- Each manager turn sends a compact snapshot to the LLM.
- The LLM returns a structured `LLMTurnResponse`.
- Backend validates the response with Pydantic and applies only bounded state changes.
- Hidden persona/profile must stay hidden until the final report or explicitly internal/admin-only views.

**Current repo observed state:**

- Backend: Python package `sales-trainer-mvp`.
- Python: `requires-python >=3.12`; backend Docker image uses `python:3.13-slim`.
- Backend stack: FastAPI, Pydantic v2, pydantic-settings, Redis, SQLAlchemy, Alembic, PostgreSQL, httpx/OpenAI-compatible client.
- Frontend: React 18 + TypeScript + Vite in `frontend/`.
- Internal Admin UI: React/Vite route `/admin`, available only to `internal_admin`.
- Client cabinet: React/Vite routes under `/app`, role-aware for `client_manager` and `client_lead`.
- Runtime session state: Redis via `SessionRepository`.
- Identity/access/history data: PostgreSQL via SQLAlchemy repositories and Alembic migrations.
- Auth: HttpOnly session cookie, CSRF token for mutating browser requests, login rate limit.
- Roles: `internal_admin`, `client_lead`, `client_manager`; legacy `client_user` must be normalized as `client_manager`.
- Internal admin API path: `/api/internal/*`, protected by `internal_admin` only.
- Primary configured LLM path: Yandex-compatible persona/dialogue/judge agents via environment configuration.
- Local/demo resilience path: fake/local fallbacks remain intentionally available for development and demo recovery.
- Persona generation path: authenticated API session creation uses `PersonaGenerationService` to create hidden `PersonaProfile` from client training config and global Yandex settings in `.env`; CLI/debug fallback uses Python `PersonaGenerator`.
- Organization-scoped LLM provider configs still exist in PostgreSQL as legacy/future-enterprise groundwork; API keys remain encrypted and masked, but MVP runtime no longer depends on them.
- Public API path: `/api/*`.
- Auth path: `/auth/*`.
- Static frontend can be served by FastAPI and in Docker through nginx.
- Existing project documentation: `README.md`, `sales_trainer_mvp_docs_backlog.md`, and `docs/agent-reference/README.md`.
- Root project instructions live in `AGENTS.override.md`; keep this file synchronized with the repository state after each completed iteration.

## 2. Main entry points

Backend:

- CLI trainer: `python -m app.cli.main`
- API app: `app.api.main:create_app`
- Uvicorn local: `python -m uvicorn app.api.main:app --reload`
- Admin CLI: `python -m app.admin.cli ...`
- Settings: `app.infrastructure.config.Settings`
- Domain models/contracts: `app.domain.models`
- Session orchestration: `app.application.session_service.TrainingSessionService`
- Turn orchestration: `app.application.turn_service.TurnService`
- Reports: `app.application.report_service.ReportService`
- Persona generation service: `app.application.persona_generation_service.PersonaGenerationService`
- Runtime session repository: `app.infrastructure.session_repository`
- LLM adapter: `app.infrastructure.llm_client`
- Persona generator adapter: `app.infrastructure.persona_generator_client`
- Identity/auth: `app.identity.*`
- Client access/config ownership: `app.access.*`
- Internal admin API: `app.internal_admin.*`
- Persistent history: `app.history.*`

Frontend:

- Location: `frontend/`
- Dev: `npm run dev`
- Build: `npm run build`
- API calls should use relative paths such as `/auth/login`, `/auth/csrf`, `/api/sessions`.

Infrastructure:

- Local Redis/PostgreSQL: `docker compose up -d redis postgres`
- Migrations: `alembic upgrade head`
- Production-like local stack: `docker compose up --build`
- Nginx/frontend exposed on host port `8080`.

## 3. Architecture rules

### 3.1 Layer boundaries

Keep the architecture layered:

```text
CLI / API / frontend
        ↓
application services
        ↓
domain models + business rules
        ↓
infrastructure adapters
```

Rules:

- CLI and API are presentation adapters. They must not contain core training logic.
- Domain code must not import FastAPI, Redis, SQLAlchemy sessions, OpenAI/Yandex clients, or frontend concepts.
- Application services coordinate use cases, repositories, LLM clients, summaries, reports, and state transitions.
- Infrastructure implements adapters: Redis, PostgreSQL, LLM provider, config, logging, static serving.
- When adding frontend behavior, prefer API DTO/projection changes over leaking backend internals.

### 3.2 State ownership

The backend is the source of truth.

- `TrainingSessionState` is canonical.
- `interest_score` is stored and clamped by backend.
- `StatePatch` is a proposal, not authority.
- `apply_state_patch()` must clamp bounded numeric deltas and append list values safely.
- `state_version` must remain meaningful for optimistic concurrency.
- Redis TTL behavior must be preserved unless intentionally changed.
- Do not allow the provider response to set arbitrary state keys.

### 3.3 LLM contract

The LLM adapter must return `LLMTurnResponse`.

- Treat all provider output as untrusted.
- Parse and validate provider output through Pydantic.
- For external providers, prefer JSON schema / structured output where available.
- Retry invalid structured output with a clear “JSON only” instruction.
- Never depend on natural-language provider text for application control flow.
- Never place secrets into prompts.
- Do not log full prompt payloads unless explicit debug mode is enabled.
- Keep `FakeLLMClient` deterministic enough for tests.

Persona generation has a separate contract:

- Persona Generator LLM returns `PersonaGenerationOutput`.
- The output must validate into `PersonaProfile` before it enters runtime state.
- Persona Generator LLM must not simulate dialogue turns.
- Dialogue Simulator LLM must not regenerate or mutate the hidden persona.
- Raw persona-generation prompts, payloads, responses, and provider secrets must not appear in client endpoints, usage events, normal logs, or frontend state.
- Legacy Python `PersonaGenerator` remains only fallback/debug-compatible path, not the preferred production path.

### 3.4 Hidden persona and public projections

The hidden profile is a simulation asset, not trainee-visible state.

Allowed during active session:

- public brief
- current stage
- interest score/band
- visible objections
- discovered pains
- discovered decision criteria
- discovered constraints/current process only if discovered through conversation
- buying signals
- trainee-visible turn history

Forbidden during active session:

- exact hidden role unless discovered
- `authority_level` unless discovered
- latent pains unless discovered
- hidden constraints unless discovered
- full `PersonaProfile`
- raw LLM payload containing hidden profile
- internal notes from provider unless explicitly admin/debug and protected

If changing DTOs, verify `app.application.projections` and tests.

### 3.5 Auth/access model

- Browser auth uses HttpOnly session cookie.
- Mutating authenticated `/auth/*` and `/api/*` requests require CSRF token header.
- Client users must access only their own sessions through `training_session_ownership`.
- `persona_id` is internal-admin/debug-compatible only; normal client users must use training config policy.
- Passwords must be hashed with Argon2id.
- Raw login session tokens must not be stored; store token hashes.
- Login failures should not reveal whether the email exists.
- Audit logs are useful but must not store passwords, raw tokens, or full secret payloads.
- Client-side roles are `client_lead` and `client_manager`; do not create `internal_admin` through organization user endpoints.
- Internal admin endpoints must stay under `/api/internal/*` and require `require_internal_admin`.

### 3.6 Persistent history

- Redis remains the source of truth for active runtime session state.
- PostgreSQL is the source of truth for durable training history, reports, usage events, and analytics inputs.
- Authenticated API session create/turn/finish/report flows must write history fail-fast.
- CLI local training may remain runtime-only unless explicitly wired to DB.
- Client-facing history DTOs must not expose `persona_snapshot`, raw LLM payloads, raw LLM responses, provider secrets, or hidden persona fields.

## 4. Development workflow for Codex

### 4.1 Start-of-iteration checklist

At the beginning of each task:

1. Restate the target in one sentence internally.
2. Run or inspect `git status --short` when shell access is available.
3. Inspect relevant files before editing.
4. Find existing tests around the touched behavior.
5. Identify the smallest safe change.
6. Prefer modifying existing conventions over introducing new patterns.
7. If repo state differs from this file, trust the code and update this file at the end.

### 4.2 Implementation checklist

During implementation:

- Before changing code, read `docs/agent-reference/README.md` and the relevant reference file under `docs/agent-reference/`.
- Keep patches small.
- Avoid broad refactors mixed with feature work.
- Preserve public contracts unless the task requires changing them.
- Add or update tests near the changed layer.
- Update `README.md` only when setup, commands, API behavior, or user-facing flow changes.
- Update `docs/agent-reference/` when changing architecture, public DTOs, runtime flow, auth/security, LLM/STT behavior, or tests.
- Update `sales_trainer_mvp_docs_backlog.md` if product/architecture roadmap materially changes.
- Add Alembic migrations for schema changes; do not edit applied migrations unless the migration has not been shared/used.
- Do not add new production dependencies without a clear reason.
- If adding dependency, update lockfiles where applicable and explain why the dependency is necessary.
- Do not introduce background jobs, queues, external services, or payment logic unless explicitly requested.

### 4.3 End-of-iteration checklist

Before final response or PR handoff:

1. Run the narrowest relevant tests first.
2. Run the broader required checks when practical.
3. Update **Current state** in this file.
4. Update **Backlog** in this file:
   - move completed items to Done,
   - add newly discovered issues,
   - mark blocked items with reason,
   - adjust priority if the work changed risk/order.
5. Update **Rules changelog** if a new convention/invariant was discovered.
6. Summarize:
   - changed files,
   - commands run,
   - test results,
   - known risks,
   - next suggested step.
- Never paste secrets, raw tokens, full credentials, or sensitive payloads into the final response.

Important: Codex usually loads AGENTS instructions at session start. Updating this file helps future Codex sessions and keeps the project state explicit, but a running session may need restart to consume new instruction text.

### 4.4 AGENTS maintenance protocol

Because this file is loaded as persistent project context, keep maintenance updates surgical:

- Update only facts changed or discovered during the current iteration.
- Do not rewrite the whole file for style churn.
- Keep backlog items short and actionable.
- Move long explanations to `README.md`, `sales_trainer_mvp_docs_backlog.md`, or a dedicated docs file if this file approaches the project-doc limit.
- If code and this file conflict, trust the code for the current task, then fix this file before handoff.

### 4.5 Operational assumptions

Treat the following as normal unless the code contradicts them or the user asks for a change:

- `.env` is filled and checked manually before deployments.
- `APP_ENV`, `LLM_BACKEND`, Yandex credentials, fallback flags, STT flags, cookie security, and binary paths are intentionally environment-controlled.
- Production/VPS deployment may override Docker port binding, for example `127.0.0.1:8080:80`.
- Live Yandex smoke tests, CI, backend tests, frontend build/tests, and smoke checks are expected operational practice, not backlog items by themselves.
- Local/demo fake fallbacks are acceptable for development and demo resilience; they become a defect only if production configuration accidentally permits them where it should not.

Do not open backlog work only for:

- removing fake fallback globally;
- forcing `.env.example` as a deployment blocker;
- treating `AUTH_COOKIE_SECURE` as a code bug without checking target environment;
- treating STT disabled by environment as a defect;
- treating local Docker port exposure as a production blocker when deployment override is expected.

### 4.6 Definition of done

A backlog item is done only when:

1. The implementation stays scoped and avoids unrelated rewrites.
2. Relevant backend tests pass, or the final response says exactly why they were not run.
3. Frontend build/tests pass if frontend code was touched.
4. New behavior has focused tests where practical.
5. Hidden-persona vs public DTO boundaries remain intact.
6. Auth, CSRF, role checks, and session ownership checks are not weakened.
7. Redis runtime state and PostgreSQL persistent-history interactions were considered if the task touched runtime/session flow.
8. README or local instructions are updated if operational behavior changed.
9. The completed, changed, or obsolete backlog item is updated in this file.

## 5. Commands and validation

### 5.1 Python setup

Preferred local setup:

```bash
python -m venv .venv
```

Windows activation and install:

```bash
.venv\Scripts\activate
python -m pip install -e .
```

Linux/macOS activation and install:

```bash
source .venv/bin/activate
python -m pip install -e .
```

### 5.2 Backend checks

Run relevant tests:

```bash
pytest
```

Useful targeted examples:

```bash
pytest tests/unit/test_models.py
pytest tests/unit/test_state_update.py
pytest tests/unit/test_llm_client.py
pytest tests/integration/test_turn_service.py
pytest tests/integration/test_api_routes.py
pytest tests/integration/test_auth_routes.py
```

Run API locally:

```bash
alembic upgrade head
python -m uvicorn app.api.main:app --reload
```

Smoke checks:

```bash
curl -i http://localhost:8000/auth/me
curl -i http://localhost:8000/auth/csrf
curl -i http://localhost:8000/api/health
```

Expected:

- `/auth/me`: 401 JSON if unauthenticated.
- `/auth/csrf`: 200 JSON with `csrf_token`.
- `/api/health`: 200 JSON `{"status":"ok"}`.

### 5.3 Frontend checks

From `frontend/`:

```bash
npm install
npm run build
```

Use `npm install` only when needed. Do not churn `package-lock.json` unless dependencies changed or install updated it intentionally.

### 5.4 Docker checks

For production-like local stack:

```bash
docker compose up --build
```

For infra only:

```bash
docker compose up -d redis postgres
```

When touching Docker/nginx/static serving, also run or update:

```bash
pytest tests/integration/test_nginx_config.py
pytest tests/integration/test_static_frontend.py
```

### 5.5 Check selection by change type

- Domain model/rules: unit tests for models, interest, stages, state update, projections.
- Turn/session logic: unit + integration tests for session/turn service.
- LLM adapter: unit tests for parsing, schema, retries, sanitization; no live cloud dependency in normal tests.
- Auth/access: identity security tests + auth route tests + access repository tests.
- API schema/routes: API integration tests.
- Frontend UI/API calls: `npm run build`; add/update frontend tests if a test framework is introduced.
- Internal admin UI changes: `npm run build`; verify no hidden persona/raw LLM payload/API key exposure in rendered DTOs.
- Client cabinet changes: `npm run build`; verify manager/lead route visibility and no use of `/api/internal/*` from client UI.
- Migrations: migration upgrade against local PostgreSQL when possible.
- Docs-only: no test required, but verify links/commands are not obviously stale.

## 6. Coding style

### 6.1 Python

- Use Python 3.12+ syntax.
- Prefer type hints and explicit return types.
- Use Pydantic v2 APIs: `model_validate`, `model_validate_json`, `model_dump`, `model_dump_json`.
- Prefer `Field(default_factory=list)` over mutable defaults.
- Use `ConfigDict(extra="forbid")` for provider/API contracts where unknown fields should be rejected.
- Raise domain-specific errors from domain/application code; translate to HTTP errors in API layer.
- Keep functions short enough to reason about.
- Prefer named helper functions for repeated business rules.
- Avoid speculative abstractions and one-use “framework” classes.
- Do not swallow exceptions that should fail startup in staging/prod.
- Logging must be structured enough to debug and sanitized enough for production.
- Always comment every function and code block for further reliability to check and/or finding what to fix

### 6.2 FastAPI/API

- Keep route handlers thin.
- Use dependency injection through existing dependency modules.
- Return DTOs/projections, not domain objects directly when hidden fields exist.
- Keep error response shape consistent.
- Preserve request ID behavior.
- Preserve CSRF middleware behavior.
- Do not add permissive CORS unless the deployment model explicitly needs it.

### 6.3 SQLAlchemy/Alembic

- Use repositories for DB access.
- Keep transactions explicit and predictable.
- Avoid raw SQL unless justified.
- Add indexes/constraints for ownership and lookup paths.
- Migrations must be reversible where practical.
- Never store raw passwords or raw session tokens.

### 6.4 Redis/session repository

- Preserve key namespace: `sales_trainer:session:{session_id}` unless intentionally migrated.
- Preserve TTL for active session keys.
- Keep optimistic concurrency checks intact.
- Do not split state/turn storage unless the task explicitly requires it and tests cover resume/history behavior.

### 6.5 Frontend

- Use TypeScript types for API responses/requests.
- Keep auth tokens out of localStorage/sessionStorage.
- Use relative API URLs; dev proxy and production nginx/FastAPI serving rely on this.
- Fetch CSRF token before mutating authenticated requests that require it.
- Handle 401/403/409/422 as first-class UI states.
- Do not reveal hidden persona fields in active-session UI.
- Do not reveal hidden persona snapshots, raw LLM payloads, raw LLM responses, full API keys, or temporary passwords in admin UI.
- Client UI must not call internal admin APIs; add client-facing endpoints for lead/team data instead.
- Keep UI simple and production-readable; avoid adding UI libraries without explicit value.

## 7. Security rules

### 7.1 Secrets and config

- `.env` is local only. Never commit it.
- Commit only safe examples such as `.env.example`.
- Mask API keys in logs. Existing pattern: show a short prefix/suffix only.
- Do not print full `DATABASE_URL` if it may contain real credentials.
- Do not include secrets in test snapshots.
- `SECRET_ENCRYPTION_KEY` is required for non-local operations that store/decrypt organization LLM provider secrets.
- LLM provider API keys must be encrypted in PostgreSQL and returned only as `has_api_key` plus masked preview.

### 7.2 Auth/session security

- Keep `auth_cookie_secure=true` for production-like environments.
- Keep HttpOnly auth cookie.
- Keep SameSite at least `lax` unless there is a reviewed cross-site requirement.
- CSRF cookie may be readable by JS only for token submission; auth cookie must not be readable by JS.
- Session logout must revoke server-side session.
- Expired sessions should be cleanup-capable.

### 7.3 LLM/prompt security

- Manager messages are untrusted input.
- Provider output is untrusted input.
- Prompt injection from manager text must not override system/developer instructions.
- LLM must not choose access rights, ownership, prices, payment status, or security decisions.
- Never send raw credentials, auth cookies, internal admin passwords, or secrets to LLM providers.
- In staging/prod, fake fallback should be disabled unless explicitly accepted.

### 7.4 Data exposure

- Treat client configs, training histories, session ownership, and persona policies as tenant-sensitive.
- Do not expose another client’s scenario/config/session through API.
- Do not include hidden persona in browser state.
- Do not add admin endpoints without `require_internal_admin`.
- For production in Russia or with Russian clients, assume personal data and commercial data may be regulated; collect the minimum needed and keep audit/security behavior explicit.

## 8. Product behavior rules

### 8.1 Training philosophy

The trainer should reward discovery-first selling, not pitch spam.

Good manager behavior:

- asks who the client is and what they control,
- clarifies current process,
- discovers pain before presenting,
- ties value to the client’s situation,
- handles objections without pressure,
- proposes next step only when interest/readiness is high enough.

Bad manager behavior:

- generic pitch,
- long monologue,
- pressure/urgency manipulation,
- premature meeting push,
- ignoring role/authority,
- claiming impossible guarantees.

### 8.2 Persona generation

- Generated persona should be internally consistent.
- Role is hidden from the trainee until discovered or final report.
- For accounting outsourcing / outsourced CFO training, persona facts should reflect Russian B2B realities where relevant.
- Avoid impossible scenarios where the contact cannot ever influence the target action unless that is intentionally a training scenario.
- Role, authority, objections, pains, constraints, decision criteria, and communication style should support realistic dialogue.

### 8.3 Reports/evaluation

- Reports should distinguish observed trainee behavior from hidden truth.
- Do not overclaim model certainty.
- Evaluation should cite actual turns where practical.
- Rule-based evaluator is acceptable for MVP, but keep it replaceable by a future judge model.

## 9. Backlog

Maintain this backlog after every iteration.

### P0 — Data consistency and runtime correctness

#### P0.1 Add idempotency for manager message submission

- [x] Add an optional idempotency key to `POST /api/sessions/{session_id}/messages`.
- [x] Frontend should generate a stable per-send key.
- [x] Backend should detect repeated submissions for the same session/user/key.
- [x] Repeated identical request should return the already processed result where possible.
- [x] Conflicting reuse of the same key with different payload should return a controlled `409`.
- [x] Keep backward compatibility when the key is missing unless a stricter migration is explicitly requested.
- [x] Add tests for duplicate key, conflicting key, and no-key legacy behavior.

#### P0.2 Add reconciliation or retry path for Redis -> PostgreSQL history write gap

- [x] Make Redis/runtime vs PostgreSQL/history divergence visible and recoverable instead of only logging it.
- [x] Add a deterministic retry, reconciliation, or recovery path after history write failure following a successful Redis turn update.
- [x] Ensure the client receives a controlled error that does not encourage blind duplicate resubmission.
- [x] Add tests simulating history write failure after Redis update.
- [x] Keep recovery surfaces free of hidden persona data.

### P1 — Security and abuse hardening

#### P1.1 Add password policy

- [x] Keep admin-created and reset user passwords as random one-time passwords intended only for the first login.
- [x] Preserve the first-login flow where a user must pass through the password-change screen and save a permanent password before normal work.
- [x] Add a simple permanent-password validator: minimum 8 characters, Latin letters and digits only; case and special-character complexity are not required.
- [x] Reject `new_password == current_password` and return user-friendly validation errors.
- [x] Apply the same permanent-password validation to relevant password-change flows without logging or returning raw passwords.
- [x] Add tests for invalid characters, too-short password, same-password rejection, valid password, and first-login forced-change behavior.

#### P1.2 Add rate limiting for public lead endpoint

- [x] Add configurable rate limiting for `POST /api/leads` by IP and optionally email/phone.
- [x] Keep honeypot/spam-marking behavior and attribution whitelist behavior.
- [x] Return controlled `429` responses.
- [x] Add tests for normal submission, honeypot spam marking, and rate limit behavior.

#### P1.3 Add rate limiting / queue protection for STT endpoint

- [ ] Preserve per-user concurrency and non-streaming batch STT flow.
- [ ] Add or verify per-user time-window rate limiting for `/api/speech/transcribe`.
- [ ] Add or verify small-server global protection for expensive STT calls.
- [ ] Return controlled `429` or `409` with frontend-usable errors.
- [ ] Add tests for too many requests and concurrent request behavior.

#### P1.4 Use trusted proxy IP extraction for audit/rate limit

- [ ] Add a small trusted-proxy helper for client IP extraction.
- [ ] Use `X-Forwarded-For` / `X-Real-IP` only when the immediate peer is a trusted proxy/network.
- [ ] Fall back to `request.client.host` for direct/untrusted peers.
- [ ] Reuse this helper consistently for login audit, rate limits, leads, and STT where applicable.
- [ ] Add tests for direct request, trusted proxy forwarding, and untrusted spoofed headers.

### P2 — Maintainability and frontend refactoring

#### P2.1 Remove shadowed legacy fake LLM implementation

- [ ] Remove dead/shadowed fake LLM code or rename it explicitly as legacy if it still has a purpose.
- [ ] Keep one clear active fake LLM implementation path.
- [ ] Preserve local fake-mode behavior unless an intentional change is requested.

#### P2.2 Split large frontend stylesheet

- [ ] Split `frontend/src/styles.css` into smaller stylesheet modules such as tokens/base/landing/auth/client/trainer/report/admin.
- [ ] Preserve current visuals and existing class names unless a small targeted rename is necessary.
- [ ] Keep CSS import order deterministic.
- [ ] Verify login, landing, client cabinet, trainer, report modal, and admin surfaces still render correctly.

#### P2.3 Replace hand-written router with `react-router-dom`

- [ ] Introduce `react-router-dom` and migrate the manual pathname/pushState/replaceState router.
- [ ] Preserve existing public, client, history-detail, team, settings, balance, and admin routes.
- [ ] Preserve auth bootstrap behavior, post-login redirects, and role restrictions.
- [ ] Ensure protected routes still redirect correctly after the migration.

#### P2.4 Clean trainer session localStorage on logout/account switch

- [ ] Clear or namespace `salestrainer.currentSessionId` on logout/account switch.
- [ ] Prevent one browser user from trying to restore another user's previous session.
- [ ] Handle forbidden/not-found restore responses gracefully.
- [ ] Keep server-side ownership checks unchanged.

#### P2.5 Clarify fate of legacy/future `llm_provider_configs`

- [ ] Keep README and local agent instructions explicit that MVP runtime uses global env-based Yandex settings plus client `persona_generation_context`.
- [ ] Ensure admin UI/API does not imply organization-level provider configs affect the active MVP runtime unless that becomes true.
- [ ] Do not partially wire `llm_provider_configs` back into runtime without an explicit product decision.

### P3 — Product and analytics improvements

#### P3.1 Improve analytics from saved judge payloads

- [ ] Use `training_reports.report_payload` to derive richer safe aggregates such as judge score, weakest/strongest skill, trend over time, completion rate, average final interest, and manager ranking for `client_lead`.
- [ ] Keep client/team analytics limited to safe aggregates; never return hidden persona snapshots or raw LLM data.
- [ ] Keep empty states clear when no saved judge payload exists.

#### P3.2 Add prompt/schema version metadata

- [ ] Persist dialogue schema version metadata.
- [ ] Persist persona-generation schema version metadata.
- [ ] Persist judge schema/prompt version metadata where available.
- [ ] Keep version metadata in safe internal fields without exposing provider payloads.

### Done

- [x] CLI trainer exists.
- [x] FastAPI API exists.
- [x] React/Vite frontend exists.
- [x] Redis runtime session repository exists.
- [x] PostgreSQL identity/access layer exists.
- [x] Alembic migrations exist.
- [x] Auth endpoints exist: login, logout, me, csrf.
- [x] HttpOnly cookie + CSRF pattern exists.
- [x] Admin CLI exists for client/user/config operations.
- [x] Fake LLM working path exists.
- [x] Yandex/OpenAI-compatible adapter exists with structured parsing and sanitized metadata logging.
- [x] Basic unit/integration test structure exists.
- [x] Landing `/` desktop hero compacted so H1, subtitle, CTA, and product mockup fit the first 1366×768 screen.
- [x] Landing audience section uses role/outcome split layout instead of four equal cards.
- [x] Landing product flow uses a process-line layout instead of four equal cards.
- [x] Landing screenshots refreshed: desktop first/full and mobile first/full PNGs.
- [x] Landing final polish: product-like hero mockup, stronger manager dashboard anchor, stronger conversion block, compact mobile/full page.
- [x] Landing final visual pass: primary/secondary/ghost CTA hierarchy, lighter H1, calmer mockup topbar, denser long page and FAQ.
- [x] Landing hero layout locked: two CTA buttons plus login text link, unified dashboard mockup, desktop/mobile first-screen screenshots refreshed.
- [x] Landing `/` rebuilt into a modular product-first tile/bento page with separate hero, problem, demo, evaluation, management, scenarios, pilot, CTA, FAQ, and footer sections.
- [x] Public landing now uses a shared color-token layer with the client cabinet and includes an autonomous `ProductDemo` plus Vitest smoke coverage for hero/demo/CTA rendering.
- [x] Landing `/` hero is now chat-only, while evaluation and bento-report live in a separate showcase block below as independent tile scenes.
- [x] Landing `/` first small visual iteration lightened shared surfaces and tightened section rhythm without changing hero/showcase composition.
- [x] Landing `/` typography pass reduced oversized hero/section headings and normalized card/body text rhythm.
- [x] Landing `/` hero-fit pass constrained hero heading to a calmer multi-line block, equalized hero card heights, and fixed visible split-section alignment issues.
- [x] Landing `/` hero no longer duplicates the cabinet login CTA, and showcase `ProductDemo` uses one visible auto-rotating slide with selector tabs.
- [x] Landing `/` hero buttons align to the bottom of the hero text tile, showcase notes were removed, and the showcase intro now aligns with the one-slide demo surface with smooth selector/slide transitions.
- [x] Landing `/` FAQ heading no longer shows the internal placeholder line about a calm final block below CTA.
- [x] Landing `/` mobile showcase slider now keeps a stable slide area height so auto-rotation does not jump the page.
- [x] Landing `/` mobile hero chat and showcase slider now use fixed-height mobile containers with internal overflow to prevent content-driven page jumps.
- [x] Internal Admin Foundation backend exists under `/api/internal/*`.
- [x] Role model includes `internal_admin`, `client_lead`, `client_manager`; legacy `client_user` maps to `client_manager`.
- [x] Organization, organization user, training config, user config assignment, LLM provider config, and audit-log internal admin APIs exist.
- [x] `/auth/change-password` exists and `must_change_password` is returned by `/auth/login` and `/auth/me`.
- [x] First `internal_admin` bootstrap CLI exists: `python -m app.admin.cli create-internal-admin ...`.
- [x] Organization LLM provider API keys use `cryptography.Fernet` at rest.
- [x] `EmailStr` support is explicit via `email-validator` dependency and covered by FastAPI app import smoke test.
- [x] Persistent Training History backend foundation exists in `app.history`.
- [x] PostgreSQL history tables exist: `training_sessions`, `training_turns`, `training_reports`, `usage_events`.
- [x] Authenticated `/api/sessions/*` flow writes persistent history and usage events.
- [x] Client-facing history endpoints exist under `/api/history/*` with public-safe DTOs.
- [x] Internal admin history/usage endpoints exist under `/api/internal/*`.
- [x] Internal Admin UI exists at `/admin` for `internal_admin`.
- [x] Admin UI covers organizations, users, training configs, persistent history, usage analytics, and audit log.
- [x] Client cabinet exists under `/app` with dashboard, trainer, history, analytics, team, balance, and settings routes.
- [x] Client-facing team analytics endpoints exist under `/api/team/*` and do not use `/api/internal/*`.
- [x] Separate LLM persona generation flow exists for authenticated API session creation.
- [x] `PersonaGenerationInput` and `PersonaGenerationOutput` contracts exist and validate generated personas through `PersonaProfile`.
- [x] Legacy Python `PersonaGenerator` remains available as local/fake fallback and CLI-compatible path.
- [x] Demo-ready LLM config stores separate persona-generation and dialogue Yandex settings with encrypted keys.
- [x] MVP runtime uses global Yandex persona/dialogue agents from `.env`; training config stores `persona_generation_prompt` business context.
- [x] Internal Admin UI primary flow no longer requires organization-level LLM settings; prompt is managed on training config.
- [x] Training configs include `product_line` and send it in `PersonaGenerationInput` alongside scenario and `persona_generation_prompt`.
- [x] Admin UI no longer exposes LLM provider config endpoints, API key fields, agent/folder fields, master prompt fields, or JSON template fields in the primary organization flow.
- [x] Generated persona business rules reject non-LPR personas, disallowed roles, incompatible product lines, and empty required business fields.
- [x] `/api/leads` persists landing form submissions with EmailStr validation, query-param whitelist, and honeypot spam marking.
- [x] Authenticated API session creation compensates Redis runtime session and ownership if persistent history creation fails.
- [x] GitHub Actions CI workflow exists for backend tests, frontend build, and migration upgrade.
- [x] Trainer final report UI now opens as a modal overlay with a reopen button rail instead of rendering a long inline text block in the left panel.
- [x] Trainer workspace is adaptive inside `/app/trainer`: side panels stay pinned near the client sidebar, chat fills the remaining width, and the report reopen action lives in the trainer header instead of a separate rail.
- [x] Trainer chat workspace now keeps the route shell fixed-height and scrolls only the message list inside `ChatWindow`; header and composer stay visible during long conversations.
- [x] Voice input MVP exists as a pre-send STT layer: recorded audio is transcribed by `/api/speech/transcribe`, inserted into the trainer textarea, and still requires manual send.
- [x] Frontend shared branding uses `frontend/public/logo.svg` for the public landing, client/admin sidebars, and browser favicon.
- [x] Client history and trainer modal now share one report surface: valid structured judge payloads render as bento reports, while legacy plain text appears only as a bounded fallback.
- [x] Client cabinet navigation temporarily hides the Balance/usage section while preserving the route/component code as future billing/limits groundwork.
- [x] Client/admin UI labels now centralize role/status/scenario/provider/audit/usage naming and avoid raw technical keys in normal user-facing surfaces.
- [x] Client analytics `/app/analytics` now uses a full-width bento layer with real backend-provided 7-day dynamics, while `/app/history/{session_id}` no longer renders the separate summary/public-brief block and shows started-at date/time in the H1; 7-day session metrics are computed separately from report joins so training reports cannot duplicate session counts.
- [x] Internal Admin now has a dedicated permalink user-analytics screen at `/admin/organizations/{organization_id}/users/{user_id}/analytics`, backed by an organization-scoped `/api/internal/organizations/{organization_id}/users/{user_id}/analytics` endpoint that reuses client analytics logic and returns recent public-safe history.
- [x] Returning from internal-admin user analytics now preserves organization context via `/admin/organizations/{organization_id}?tab=users`, so the back action reopens the Users tab instead of the organization overview.
- [x] Internal Admin training config UI is simplified to name plus persona-generation context.
- [x] Backend training config runtime no longer uses legacy `default_scenario_id`, `persona_policy`, `ui_config.allowed_scenarios`, or `limits` as business sources; DB columns remain for compatibility.
- [x] Internal-admin training config API/DTO now exposes only `id`, `client_account_id`, `name`, `is_active`, `persona_generation_context`, `created_at`, and `updated_at`; legacy request fields are rejected while service-level create still fills legacy DB columns internally.
- [x] Final training-config storage cleanup is completed: `client_training_configs` no longer stores legacy scenario/policy/ui/limits/provider columns, `RuntimeTrainingConfig` is minimal, and runtime still uses settings or explicit `scenario_id`.
- [x] Local `development` branch was rebased onto `origin/main` after PR #18 landed on `main`; no source behavior was changed by this maintenance step.
- [x] Runtime/history turn-write reconciliation now marks pending Redis sessions, returns controlled `409` conflicts, and lazily replays the latest turn into PostgreSQL on the next `resume`/`messages`/`finish` action without exposing hidden persona data.
- [x] Message submission idempotency now accepts optional `idempotency_key`, stores a bounded recent result cache in runtime session state, returns the saved turn result for duplicate same-payload retries, rejects conflicting key reuse with `409`, and keeps no-key legacy duplicate behavior unchanged.

## 10. Current state

Last updated: 2026-05-09 by ChatGPT after adding the agent-facing reference pack.

Observed in repository state:

- Repository: `kneadman/salestrainer`, default branch `main`.
- Agent-facing documentation pack now exists under `docs/agent-reference/` with architecture, backend/frontend codemaps, API/data/security/LLM/STT/test/devops references, a change guide, and a symbol index for future agents.
- README describes a CLI/API MVP with Redis runtime sessions, PostgreSQL identity/access/history, Alembic, React/Vite frontend, Docker stack, and environment-controlled LLM/STT behavior.
- Frontend now serves the shared logo as a public Vite asset from `frontend/public/logo.svg`; visible brand marks are wired into the landing, client cabinet, internal admin sidebar, and favicon.
- Root `README.md` now points future agents to `docs/agent-reference/README.md` as the first documentation entry point.
- `pyproject.toml` lists Python package modules and dependencies.
- Core training flow is implemented through `TrainingSessionService` and `TurnService`.
- Runtime architecture expects Yandex-compatible persona/dialogue/judge agents in configured environments, while fake/local fallback paths remain intentionally available for local development and demo resilience.
- Authenticated API session creation now generates hidden personas through `PersonaGenerationService` before creating Redis runtime state, using `persona_generation_context` from training config plus global Yandex settings from `.env`.
- Training config runtime DTOs are minimal and now carry only `id`, `client_account_id`, `name`, and `persona_generation_context`; runtime scenario selection comes from `Settings.default_training_scenario_id` or an explicit session `scenario_id`.
- Generated personas now pass explicit business validation before runtime session creation: final decision-maker only, allowed role/product-line compatibility, and non-empty pains/objections/decision criteria/business context.
- `TrainingSessionState`, `PersonaProfile`, `ClientState`, `StatePatch`, and `LLMTurnResponse` define the central contracts.
- `app/domain/judgement_models.py` defines a strict post-finish Judge Layer contract and a helper that maps `TrainingSessionState` into `JudgeSessionInput` without touching finish/report integration.
- `app/infrastructure/judge_client.py` now provides a deterministic `FakeJudgeClient`, and `app/application/judgement_service.py` lets `ReportService` build structured judge payloads after finish without changing active dialogue logic.
- `app/infrastructure/judge_client.py` also includes `StructuredJudgeClient`, `build_judge_client(settings)`, and Yandex judge routing support through `yandex_judge_folder_id` / `yandex_judge_agent_id`.
- Runtime API/CLI wiring now uses `build_judge_client(settings)`; `GET /api/sessions/{session_id}/report` reuses saved `training_reports.report_payload` when available instead of recomputing it.
- `ReportService.generate_report_payload_safely(...)` now lets finish/report flows degrade to plain text reports when judge payload generation fails.
- API finish/report DTOs and client-facing history report DTOs now include optional `report_payload`, while keeping plain text report as the primary fallback contract.
- Frontend trainer/history pages now render typed structured judge payloads; the live trainer opens the final report in a modal overlay from a header-level reopen button, while admin history renders the saved structured report inline as a page block and falls back to bounded plain text only when `report_payload` is absent.
- Client portal analytics now return both all-time aggregates and backend-computed `trends_7d` windows for current vs previous 7 days, including count/rate/average deltas and directions; session-window metrics come from `TrainingSessionRecord` only, while judgement-window metrics are calculated separately from report payloads.
- Internal admin now has an organization-scoped user analytics detail flow: `/api/internal/organizations/{organization_id}/users/{user_id}/analytics` returns `{ user, analytics, history }`, verifies that the target user belongs to the organization, returns `404` on cross-organization mismatch, and keeps history payloads public-safe.
- Internal admin organization detail routing now accepts `?tab=...` query state for shareable deep links such as `/admin/organizations/{organization_id}?tab=users`; `OrganizationDetailPage` syncs its initial tab from route state without introducing a router library.
- Public API routes require authenticated user for training operations and use access checks before session operations.
- Security headers, CSRF middleware, request IDs, auth router, API router, and frontend mounting are configured in `app.api.main`.
- Password hashing uses Argon2id; login session tokens are generated securely and stored as SHA-256 hashes.
- Permanent password policy is enforced: minimum 8 characters, Latin letters and digits only; `PasswordValidationError` is raised for invalid passwords and mapped to HTTP 422 in auth routes.
- `LoginRequest` enforces Pydantic `min_length`/`max_length` constraints (`email` 1–320, `password` 1–256) for input-size hardening without applying permanent-password regex at login.
- `POST /api/leads` has configurable rate limiting by IP (and optionally email/phone) with `LeadRateLimiter`, returning controlled `429` responses; honeypot/spam-marking and query-param whitelist behavior are preserved.
- `AuthService.change_password` rejects `new_password == current_password` and validates the new password against the permanent policy before hashing.
- Admin CLI `reset-password` and internal-admin `reset_user_password`/`create_user` validate passwords through the same `validate_permanent_password` helper.
- Frontend `SettingsPage` mirrors the backend policy with client-side regex and length checks before submit.
- Docker compose includes migrate, backend, frontend/nginx, Redis, and PostgreSQL services.
- Existing tests cover domain, LLM parsing, auth, API, CLI, repositories, static frontend, nginx config, and turn/session behavior.
- Existing tests also cover internal admin role access, organization management, user management, training config assignment, LLM provider config masking/encryption, and password-change behavior.
- Frontend Vitest/jsdom coverage is present for landing, shared API client, report rendering helpers, trainer layout/report restore behavior, history report rendering, client access gating, and several internal-admin routing/detail flows.
- Persistent history is implemented in `app.history` with ORM models, repository/service layer, public projections, client routes, and internal admin routes.
- `app.infrastructure.db.import_model_modules()` imports history models for metadata-based tests.
- API history writes are fail-fast for authenticated session flows; CLI remains runtime-only.
- Session creation compensates Redis runtime state and session ownership when persistent history creation fails after runtime creation.
- Runtime sessions now carry internal `history_sync_status/history_sync_error` markers; when a turn is saved in Redis but history write fails, the API returns a controlled `409`, blocks new turns, and lazily reconciles the latest turn into PostgreSQL on the next `resume`, `messages`, or `finish` request.
- Runtime sessions now also keep a bounded internal cache of recent message-submission results keyed by optional `idempotency_key`; duplicate same-payload retries return the saved `TurnResponse`, while conflicting key reuse returns `409` and no-key requests preserve the old repeat-turn behavior.
- Pending Redis -> PostgreSQL turn reconciliation now always runs before the API serves a cached idempotent message response, so same-key retries cannot bypass durable history recovery.
- Idempotent turn processing now persists the runtime turn and its replayable public response payload in one repository save inside `TurnService.process_message(...)`; if that atomic runtime save fails for a keyed request, the API returns a controlled `409` instead of silently degrading to best-effort idempotency.
- Idempotent message-response payloads are now built from the same public projection helpers as normal session/turn API responses, so cached retries cannot leak hidden persona display names or diverge on fields like `known_pains`.
- `.env.example` now includes STT MVP environment variables for safe default-disabled speech rollout, including queue timeout, per-user concurrency, fail-closed unknown-duration policy, global concurrency naming guidance, container-default `whisper-cli`/model paths, and optional `ffmpeg`/`ffprobe` binaries.
- Frontend `/admin` is implemented with the existing lightweight path-based router, shared CSRF-aware API client, and no new frontend dependencies.
- `client_training_configs` now store `persona_generation_context` as internal-admin-only business context for persona generation.
- Admin UI client pages do not render full API keys, hidden persona snapshots, raw LLM payloads, raw LLM responses, provider config forms, or organization-level Yandex runtime settings in the primary MVP flow.
- Admin UI training config form now manages only name and `persona_generation_context`; the frontend sends only those fields to internal-admin training-config create/update endpoints.
- Internal-admin training config API/DTO now exposes only `id`, `client_account_id`, `name`, `is_active`, `persona_generation_context`, `created_at`, and `updated_at`; schema validation rejects legacy request fields with `extra="forbid"`.
- `client_training_configs` now physically stores only the active MVP fields used by runtime/admin flows; legacy `default_scenario_id`, `persona_policy`, `ui_config`, `limits`, and `llm_provider_config_id` were removed by Alembic migration `20260508_000009_drop_legacy_training_config_fields`.
- Runtime training session and persona generation use `Settings.default_training_scenario_id` unless an explicit session `scenario_id` is provided; training configs no longer influence scenario selection or persona policy through removed legacy storage fields.
- Frontend `/app` is a role-aware client cabinet; `/app/trainer` preserves the existing runtime trainer flow, now with a route-specific workspace class, adaptive two-column desktop layout, stacked tablet/mobile fallback, and local Vitest/jsdom coverage for trainer header/layout/report restore behavior.
- Frontend `/` landing now composes dedicated React sections from `frontend/src/components/landing/*` instead of one large monolithic page component.
- Public landing styling now lives behind a separate `lp-*` class namespace in `frontend/src/styles.css`, while shared root color tokens align the page with client-cabinet surfaces and CTA accents.
- Public landing includes an autonomous `ProductDemo` with three public modes: a hero chat-only loop, a showcase-scene walkthrough, and an interactive demo section, all using product-safe fake data and `prefers-reduced-motion` fallback without backend/API calls.
- Frontend `/` landing now uses reusable landing primitives in `frontend/src/components/landing/Primitives.tsx` and composes the page as independent tile groups instead of one linear stack of same-weight sections.
- Public landing copy now avoids internal UI/product terms such as `Score layer`, `Bento report`, `walkthrough`, and similar placeholder language; hero/showcase/CTA copy is shorter and more product-facing.
- Public landing surfaces are now lighter and more tiered: hero, showcase, CTA, and quiet information blocks use different visual weights instead of one uniformly dark card treatment.
- Public landing has been recovered from a broken broad visual-rhythm CSS pass: hero chips and the late grid override layer were removed, while showcase, management, and scenario blocks returned to the last stable tile composition.
- Public landing visual work is now continuing in small passes: the latest pass only lightened shared `lp-*` surfaces, softened shadows/borders, and tightened section rhythm; hero and showcase-specific composition remain separate future passes.
- Public landing typography now uses calmer `lp-*` heading scales: hero and section titles are smaller, line lengths are less narrow, and repeated card/body text has normalized line-height.
- Public landing hero now keeps the H1 on a wider, smaller text measure, stretches the hero chat visual to match the left tile height, and avoids over-stretched showcase/split-section cards.
- Public landing hero keeps the lower spacing previously occupied by the cabinet login text link, but the visible duplicate login CTA is removed because the header already owns that action.
- Public landing showcase `ProductDemo` keeps the phase selector but renders only the active panel and auto-rotates chat/scoring/report every 3 seconds after entering the viewport.
- Public landing showcase no longer renders the auxiliary "what is visible" and "why it matters" side notes; the section is now a two-column intro plus single-slide demo with smooth tab and slide transitions.
- Public landing hero text tile uses internal grid rows so CTA buttons sit at the bottom of the tile instead of leaving an unused lower gap.
- Public landing FAQ heading now omits the explanatory placeholder sentence below the title.
- Public landing mobile showcase slider uses a stable minimum slide area height with internal card overflow, preventing page jumps when chat/scoring/report slides rotate.
- Public landing mobile hero chat and showcase slider use fixed heights at mobile breakpoints; `min-height` alone was not enough because taller active content still expanded the page.
- Frontend trainer flow currently keeps STT wiring in `TrainerPage`, appends recognized text into `Composer` without auto-send, auto-opens the report modal after `/finish`, and prefers structured bento report rendering inside `TrainingReportModal` when `report_payload` matches the judge DTO shape.
- Frontend `/app/trainer` no longer presents the live workspace as a phone mockup: the right column is now a single desktop chat panel, `SessionHeader` keeps the report action before reset, and the composer exposes a visible microphone icon/button with explicit accessibility labels while preserving the existing STT wiring.
- Frontend `/app/trainer` now uses a trainer-scoped fixed-height cabinet shell and flex-column chat panel; `trainer-chat-body` wraps `error-banner + ChatWindow`, `ChatWindow` owns message scrolling, and the composer remains a direct fixed panel child.
- Frontend composer inside `/app/trainer` now behaves like a messenger input row: the textarea autosizes upward until a capped height, then scrolls internally; voice/send buttons keep a fixed 48px height and stay aligned to the textarea’s bottom edge without stretching.
- Frontend `/app/analytics` now renders a full-width bento grid with all-time values plus real `trends_7d` context; weakest-skill and skill-score summary panels are hidden from the client view without changing the backend DTO.
- Frontend `/app/history/{session_id}` no longer renders a separate summary/public-brief card; the detail H1 now uses formatted `started_at` date/time instead of a short technical session id.
- Frontend structured report guard now rejects partial/legacy payloads unless `overall_grade`, `bento_blocks[*].severity`, `skill_scores[*].severity`, and `recommendations` pass minimal runtime checks, so the trainer/admin UIs fall back cleanly instead of crashing inside bento/report lists.
- Frontend report label mapping in `frontend/src/components/reportPayload.ts` must stay as readable UTF-8 Russian copy; regression tests now pin the exact visible strings for severity and grade labels to prevent mojibake from reaching the bento report UI.
- Voice input MVP adds authenticated `/api/speech/transcribe` multipart upload with CSRF protection, bounded upload validation, temporary-file cleanup, light text normalization, always-registered controlled error handling when STT is disabled, configurable fake/`whisper.cpp` STT wiring, `ffmpeg` WAV preprocessing before `whisper.cpp`, and a local concurrency limiter with queue timeout plus per-user active-or-pending lock; the backend Docker image now bundles `whisper-cli`, the default `ggml-base.bin` model, and the required `whisper.cpp` shared libraries with an `ldd` sanity check during image build.
- STT architecture is non-streaming batch transcription: browser recording -> backend upload/probe/convert/transcribe/normalize -> text insertion into the manager composer without auto-send.
- Client lead team data is served by `app.client_portal.*` endpoints scoped to the current user's organization.
- `TrainingSessionService.start_session(...)` accepts `persona_override` for API-generated personas while CLI/debug flows still use `PersonaGenerator`.
- `/api/leads` stores landing leads in PostgreSQL instead of returning a false success without persistence.
- `.github/workflows/ci.yml` runs backend tests, frontend build, and Alembic migration upgrade.
- `frontend/src/components/Composer.tsx` now supports mic recording UX for desktop toggle and mobile press-and-hold, shows timer/transcribing/error states inline, inserts recognized text into the textarea without auto-sending, and relies on frontend auto-stop at the backend-configured 90-second MVP ceiling.
- This generated file has not been committed to the repository by ChatGPT unless the user explicitly asks to create a PR/commit.

Latest known task state:

- Task: P1.2 — Rate limiting for public lead endpoint.
- Status: completed.
- Changed files: `app/api/rate_limit.py` (new `LeadRateLimiter` with Redis and in-memory backends), `app/infrastructure/config.py` (`lead_rate_limit_attempts`/`lead_rate_limit_window_seconds`), `app/api/main.py` (wire `lead_rate_limiter` into app state), `app/api/routes.py` (apply rate limiting in `submit_landing_lead`), `tests/integration/test_api_routes.py` (rate limit tests).
- Validation run by Kimi: `pytest` — 259 passed, 1 skipped.
- Branch state after iteration:
  - `MAX_PASSWORD_LENGTH = 256` added to central policy; `validate_permanent_password` rejects passwords longer than 256 characters.
  - `ChangePasswordRequest` enforces Pydantic `min_length`/`max_length` constraints (`current_password` 1–256, `new_password` 8–256); service-level validation remains mandatory.
  - Admin CLI `_create_user` and `_create_internal_admin` now call `validate_permanent_password` and wrap `PasswordValidationError` into `AdminCLIError` (same pattern as `_reset_password`).
  - `internal_admin.service` wraps `PasswordValidationError` into `ValidationError` in `create_user` and `reset_user_password`.
  - `internal_admin.routes._handle_error` now also catches `PasswordValidationError` and returns HTTP 422 to prevent accidental 500.
  - New tests: too-long password unit test; CLI create-user and create-internal-admin rejection tests; change-password too-long rejection; internal-admin create/reset password policy violation still returns 422.
  - Existing tests updated to use compliant passwords (Latin letters and digits only).
- Known risk: persona generator provider has not been verified against a live Yandex/OpenAI-compatible account in this environment.
- Known risk: legacy `llm_provider_configs` tables/endpoints still exist and are tested for masking/encryption, but are intentionally not part of the MVP runtime flow.
- Known risk: `whisper.cpp` runtime behavior, model footprint, language quality, and actual container-level shared-library layout have not been verified on the target weak VPS in this environment; production rollout should stay disabled until that smoke test is done there.
- Known limitation: `/api/leads` has persistence and honeypot handling, but full rate limiting and CRM integration are not implemented.
- Known limitation: Redis -> PostgreSQL turn reconciliation is lazy and request-driven; there is still no background worker or operator queue for repairing orphaned pending sessions without a follow-up client action.
- Known limitation: idempotent message results are cached only in active runtime session state; once the Redis session expires or is removed, duplicate retries fall back to normal non-idempotent behavior unless a broader durable idempotency design is introduced.
- Known limitation: frontend critical paths are Russian, but a full copy-edit pass remains useful before a polished customer demo.
- Known limitation: old Redis-only sessions are not backfilled into PostgreSQL history.
- Known limitation: admin and client UI now have focused Vitest/jsdom coverage for selected routing and detail flows, but there is still no browser-level responsive/e2e coverage or screenshot baseline.
- Known limitation: client settings/password-change UI exists, but frontend tests for that form flow are still thinner than the coverage already present for trainer/history/admin flows.
- Known limitation: structured judge runtime can now be selected through `build_judge_client(settings)`, but live Judge Agent behavior is still not verified against a real provider account in this environment.
- Known limitation: structured report UI now uses a dedicated trainer modal opened from the session header, but there is still no drill-down interaction or richer visual analytics beyond the saved payload surface.
- Known limitation: backend now fails closed for non-WAV uploads with unknown duration by default, so environments missing working `ffprobe` will reject browser audio until the binary path/runtime is fixed.

## 11. Rules changelog

- 2026-05-09: Agent-reference rule added: before changing code, read `docs/agent-reference/README.md` and the relevant file under `docs/agent-reference/`; when changing architecture, public DTOs, runtime flow, auth/security, LLM/STT behavior, or tests, update that documentation in the same iteration.
- 2026-05-09: Strict idempotency rule added: for keyed `POST /api/sessions/{session_id}/messages`, the processed runtime turn and replayable public response payload must be persisted in the same runtime save; if that save fails, return a controlled retryable conflict and never silently degrade to best-effort idempotency.
- 2026-05-09: Public-safe idempotency projection rule added: cached/replayed idempotent `TurnResponse` payloads must be built from the same shared public projection helpers as normal API responses; do not hand-maintain a second DTO mapping that can leak hidden persona fields or drift on discovered-state fields.
- 2026-05-09: Idempotency/reconciliation ordering rule added: before serving a cached message submission result, `/api/sessions/{session_id}/messages` must first attempt pending Redis -> PostgreSQL reconciliation.
- 2026-05-09: Message submission rule added: `POST /api/sessions/{session_id}/messages` may accept optional `idempotency_key`; same key + same `manager_message` must replay the saved turn result, conflicting reuse must return `409`, and frontend retries must reuse the same per-send key until the draft message changes or the send succeeds.
- 2026-05-09: Runtime/history consistency rule added: if a turn is applied to Redis but durable history write fails, keep the Redis session canonical, mark it as `pending_retry`, return a controlled conflict instead of a raw `500`, and reconcile the latest turn on the next session action without exposing hidden persona or raw LLM payloads.
- 2026-05-09: Password policy rule added: permanent passwords must be at least 8 characters and contain only Latin letters and digits; `new_password == current_password` is rejected; validation is shared across `AuthService.change_password`, admin CLI reset, and internal-admin user create/reset.
- 2026-05-09: Password max-length rule added: central policy enforces `MAX_PASSWORD_LENGTH = 256`; Pydantic request models enforce the same upper bound; passwords exceeding the limit are rejected with 422 at both schema and service levels.
- 2026-05-09: Password-policy backlog rule refined: bootstrap/reset passwords are random one-time credentials for first login, and the active task is to enforce mandatory first-login replacement plus a simple permanent-password validator of 8+ Latin letters/digits.
- 2026-05-09: Operational-assumption rule added: do not open backlog work solely because `.env`, fallback mode, STT enablement, cookie security, or Docker port binding are environment-controlled; treat them as defects only when code contradicts the intended deployment model.
- 2026-05-09: Backlog reset to the current active priorities: turn idempotency, Redis/PostgreSQL reconciliation, password and endpoint abuse hardening, trusted-proxy IP handling, targeted frontend maintainability refactors, and analytics/version-metadata improvements.
- 2026-05-09: AGENTS maintenance rule clarified: keep `Backlog`, `Current state`, and repository-fact statements synchronized with the actual tree; do not leave completed frontend test/UI work marked as open.
- 2026-05-09: Internal-admin organization detail routing rule added: preserve tab context in the URL with `?tab=...` for shareable deep links and for return actions from nested admin pages; user-analytics back navigation should reopen the organization Users tab.
- 2026-05-09: Internal-admin user analytics rule added: organization user analytics should live on a dedicated permalink route `/admin/organizations/{organization_id}/users/{user_id}/analytics`, backed by `/api/internal/*`; the backend must verify the user belongs to the organization and return `404` on mismatch instead of revealing cross-organization ids.
- 2026-05-09: Client analytics aggregation hardening rule added: for `/api/client/analytics/me` 7-day trends, session counts/rates/averages must be derived from `TrainingSessionRecord` without joining report rows; judgement metrics may join reports but should defensively deduplicate by `session_id`.
- 2026-05-08: Client analytics rule added: `/api/client/analytics/me` should keep stable all-time metrics but must provide real backend-calculated `trends_7d` for client-facing dynamics; `/app/analytics` must not fabricate period deltas on the frontend.
- 2026-05-08: Client history detail rule updated: `/app/history/{session_id}` should not render a separate summary/public-brief surface, and the main H1 should use formatted started-at date/time instead of a truncated technical session id.
- 2026-05-08: Training-config storage cleanup rule added: legacy `client_training_configs` fields `default_scenario_id`, `persona_policy`, `ui_config`, `limits`, and `llm_provider_config_id` are removed from live model/storage; runtime and admin flows must keep using the minimal training-config contract unless a future product iteration explicitly reintroduces new fields.
- 2026-05-08: Backend training-config cleanup rule added: until DB cleanup is explicitly scheduled, legacy config columns may remain in models/DTOs but runtime scenario selection must use settings or explicit session request, and persona generation must not consume legacy `persona_policy`/`ui_config`/`limits` as business inputs.
- 2026-05-08: Internal-admin training-config API cleanup rule added: public create/update DTOs expose only `name` and `persona_generation_context`, response DTOs expose only minimal visible fields, and legacy storage columns stay internal until a dedicated DB migration iteration.
- 2026-05-08: Repository maintenance note: rebasing `development` onto `origin/main` after a PR merge is allowed when explicitly requested, but do not push rewritten branch history unless the user asks for it.
- 2026-05-08: Internal admin training-config UI rule added: hide legacy scenario/persona-policy/ui-config/limits fields from normal admin forms; backend now owns internal compatibility defaults and the public API must stay minimal until DB cleanup is explicitly scheduled.
- 2026-05-08: Client history summary rule added: `/app/history/{session_id}` must not render `session.summary` raw in the header; render it through a safe formatter/card that humanizes JSON strings, drops hidden/raw/secret-like keys, and keeps `public_brief` separate when present.
- 2026-05-08: Fake LLM role-answer tests must include all valid default persona role families, including purchase/закупки roles, so deterministic fake personas do not fail readability checks for valid non-sales titles.
- 2026-05-08: Trainer fixed-height rule added: `/app/trainer` should keep the outer cabinet/trainer shell height constrained and let only `ChatWindow` scroll during active dialogue; header and composer must remain visible for empty, loading, error, and long-message states.
- 2026-05-08: Client/admin UI cleanup rule added: normal user-facing React surfaces must render structured reports over legacy text, use centralized human-readable labels for backend keys, and keep billing/usage placeholders hidden until product-ready.
- 2026-05-08: Frontend branding rule added: keep the shared visible brand mark and favicon on one public Vite asset path so production builds include it.
- 2026-05-02: Initial project-specific rules created from repository scan.
- 2026-05-02: Added mandatory iteration rule: after each completed iteration, Codex must update instructions, backlog, and current state in this file.
- 2026-05-02: Added explicit hidden-persona non-leakage rule.
- 2026-05-02: Added production fail-closed rule for fake LLM and in-memory repository fallbacks.
- 2026-05-02: Review pass added git-safety, no-unrequested-commit rule, surgical AGENTS maintenance protocol, and corrected local setup commands.
- 2026-05-02: Landing marketing copy should avoid exposing internal route paths such as `/login`; use product-language descriptions instead.
- 2026-05-02: Landing user-facing copy should avoid technical terms such as endpoint, payload, config, and route.
- 2026-05-02: Internal admin APIs must live under `app.internal_admin.*` and `/api/internal/*`, and must require `internal_admin`.
- 2026-05-02: Organization-scoped LLM provider API keys must be encrypted at rest, masked in responses, and omitted from audit payloads.
- 2026-05-02: Next platform stage is Persistent Training History; keep active runtime state in Redis.
- 2026-05-04: MVP LLM runtime is global application infrastructure from `.env`; internal admin manages training business context in `persona_generation_prompt`, not per-organization API keys or agent settings.
- 2026-05-02: First `internal_admin` must be created through explicit bootstrap CLI, not organization user endpoints.
- 2026-05-02: Internal admin audit events must include organization identifiers and be committed atomically with the business change.
- 2026-05-03: Yandex environment variables remain legacy/global runtime LLM configuration until per-client LLM provider resolution is implemented.
- 2026-05-03: Persistent history rule added: Redis owns active runtime state; PostgreSQL owns durable history, reports, usage events, and analytics inputs.
- 2026-05-03: Internal Admin UI rule added: `/admin` is internal-admin-only and must never display full API keys, hidden persona snapshots, raw LLM payloads, raw LLM responses, or temporary passwords after submission.
- 2026-05-03: Client UI Analytics rule added: `/app` client cabinet must use client-facing APIs only; team data is available to `client_lead` through same-organization scoped endpoints.
- 2026-05-03: Persona generation rule added: API session creation uses a separate persona generator contract; dialogue LLM remains responsible only for turn replies and must not regenerate hidden personas.
- 2026-05-04: Demo-ready LLM config rule added: organization LLM settings use separate persona and dialogue Yandex sets; base URL is global and API keys remain encrypted/masked.
- 2026-05-04: Generated persona business validation rule added: API-created personas must be final decision-makers and satisfy allowed role/product-line and required business-context checks.
- 2026-05-04: Landing lead rule added: public lead forms must persist or clearly state they are not connected; no false accepted state for dropped data.
- 2026-05-06: MVP config cleanup rule clarified: master prompts, JSON contracts, API keys, folder IDs, and agent IDs live in Yandex/.env; training configs store only client business context.
- 2026-05-06: Terminology cleanup rule added: use `persona_generation_context` for client business context; do not reintroduce `product_line` into the training-config/persona-generation runtime flow.
- 2026-05-06: Alembic chain rule added: keep migration history linear; avoid compatibility no-op revisions when one idempotent schema migration can express the change directly.
- 2026-05-06: Judge Layer PR1 rule added: keep the first judge iteration domain-only with strict Pydantic contracts and no client/settings/report-flow/frontend changes.
- 2026-05-06: Judge Layer PR2 rule added: fake judge evaluation may populate `training_reports.report_payload`, but runtime dialogue, real judge provider settings, and frontend/UI contracts remain unchanged.
- 2026-05-06: Judge Layer PR3 rule added: structured judge provider support may exist behind a factory and reference prompt, but default runtime wiring stays on fake judge until saved-payload reuse and rollout details are handled explicitly.
- 2026-05-06: Judge Layer PR4 rule added: runtime may use `build_judge_client(settings)` after finish, but judge output must be post-validated for evidence indexes and client-facing structured payload exposure still waits for dedicated UI/API work.
- 2026-05-06: Judge Layer PR5 rule added: `/finish` and `/report` must fail open on judge payload generation errors, plain text report remains the fallback contract, and client-facing structured payload exposure is limited to optional DTO fields plus a compact summary card, not full bento UI.
- 2026-05-06: Judge Layer PR6 rule added: frontend may render typed structured report payloads inline and analytics may aggregate only saved valid `JudgeSessionOutput` payloads; invalid payloads must be ignored and the plain text report remains visible.
- 2026-05-07: Trainer report UX rule added: live trainer must keep side panels limited to runtime coaching context; final reports open in a modal overlay with an explicit reopen control, and legacy plain text stays inside bounded report surfaces only.
- 2026-05-07: Trainer workspace rule updated: `/app/trainer` should use a route-specific adaptive workspace with side panels pinned near the sidebar, chat filling the remaining width, internal chat scrolling, and the report reopen control rendered inside `SessionHeader` rather than a separate report rail.
- 2026-05-07: Admin history report rule added: render saved `report_payload` as an inline structured report block on the session page; use plain text only as a bounded fallback when no structured payload exists.
- 2026-05-07: Voice input rule added: speech transcription is a pre-send UX layer only; `/api/speech/transcribe` must not create turns, write history, mutate Redis session state, or auto-send recognized text to the dialogue LLM.
- 2026-05-07: STT deployment-safety rule added: speech router must always exist and return a controlled error when STT is disabled, synchronous transcription/conversion must stay off the event loop, browser audio must be normalized to WAV before `whisper.cpp`, container images must include the required `whisper.cpp` shared libraries and fail build-time `ldd` checks when they are missing, optional `session_id` must respect session ownership, and concurrency must use a bounded global queue plus per-user active-or-pending conflict rather than a bare process-wide semaphore.
- 2026-05-07: Frontend TDD rule added for trainer UI work: add or update lightweight Vitest/jsdom coverage for DOM structure and state transitions first, and leave breakpoint fidelity to build plus manual responsive smoke checks rather than jsdom size assertions.
- 2026-05-07: Trainer chat-panel layout rule added: when the trainer panel uses a 3-row grid, transient error UI must live inside a dedicated chat-body wrapper with `ChatWindow`, so errors do not create implicit grid rows or push the composer out of the intended layout.
- 2026-05-07: Composer UX rule added: trainer textarea should autosize upward like a messenger input, cap at a bounded max height with internal scroll, and keep voice/send controls fixed-height and bottom-aligned rather than stretching with multiline input.
- 2026-05-07: Frontend merge-recovery rule added: `frontend/src/types.ts` is the shared contract source for judge/STT DTOs; conflict resolution must preserve structured report and speech DTO exports rather than narrowing them back to plain `Record<string, unknown>`.
- 2026-05-07: Trainer presentation rule added: `/app/trainer` should render the live dialogue as a desktop chat workspace panel rather than a phone mockup, and the composer microphone control should stay visually prominent, icon-based, and accessibility-labeled while reusing the existing STT flow.
- 2026-05-07: Structured-report runtime guard rule added: frontend bento/report rendering must reject partial or legacy payloads before JSX access; at minimum validate `recommendations` plus known grade/severity enum values so malformed saved payloads degrade to the existing fallback surface instead of breaking the modal/UI.
- 2026-05-07: Structured-report copy rule added: visible Russian labels in frontend report helpers must remain readable UTF-8 strings, and exact-string tests should pin them to catch encoding regressions before deploy.
- 2026-05-08: Landing rework rule added: public `/` should use a dedicated `lp-*` CSS namespace plus shared root theme tokens, so landing experiments do not leak styles into cabinet/trainer surfaces while keeping one accent/system palette.
- 2026-05-08: Landing demo rule added: hero may use an autoplay presentation mode, but any public demo animation must remain deterministic, backend-free, reduced-motion-safe, and visually consistent with the cabinet/trainer surfaces.
- 2026-05-08: Landing composition rule added: hero must stay chat-only, while evaluation/report visuals belong to a separate showcase block and the rest of the page should read as distinct tile groups rather than one linear strip.
- 2026-05-08: Landing copy/tone rule added: public landing text must avoid internal design/dev terms and placeholder labels; surfaces should use visibly different lightness tiers so the page does not read as one dark monolith.
- 2026-05-08: Landing rhythm rule added: after the hero, the page should alternate composition patterns rather than repeating the same large-lead-plus-grid layout; showcase should stay compact enough not to dominate the entire page height.
- 2026-05-08: Landing recovery rule added: avoid broad late CSS override blocks that rewire several section grids at once; when a visual pass breaks layout, recover to the last stable composition before iterating further.
- 2026-05-08: Landing iteration rule added: polish `/` in small sequential passes, first shared surfaces/rhythm, then hero, then showcase; do not add another broad late CSS layer that changes all three at once.
- 2026-05-08: Landing typography rule added: public `/` headings should read as normal product UI headings, not hero-scale blocks repeated through the page; prefer smaller clamps and wider line lengths before changing layout.
- 2026-05-08: Landing hero-fit rule added: hero H1 should stay readable in roughly three lines on desktop; match paired hero tile heights before adding more visual detail.
- 2026-05-08: Landing showcase rule added: when the showcase feels crowded, keep selector tabs but show one product panel at a time with deterministic 3-second rotation instead of rendering all panels simultaneously.
- 2026-05-08: Landing showcase simplification rule added: if the one-slide showcase carries the message, remove adjacent explanatory note cards and align the intro tile height with the slider instead of filling the area with secondary cards.
- 2026-05-08: Landing mobile slider rule added: auto-rotating landing sliders must reserve stable height on mobile so slide changes do not shift the page while a user is reading or scrolling.
- 2026-05-08: Landing fixed-height mobile rule added: for animated mobile landing panels, prefer explicit `height` plus internal overflow over `min-height` when content length varies between animation states.

## 12. Final response format for Codex

When finishing a task, respond in Russian unless the user asked otherwise.

Use this structure:

```text
Сделал:
- ...

Проверил:
- `command` — passed/failed/not run + reason

Изменил файлы:
- `path` — why

Риски/заметки:
- ...

Следующий разумный шаг:
- ...
```

Do not be overly formal. Be direct, practical, and honest.

1. СИСТЕМНАЯ ИНСТРУКЦИЯ: СПРИНТ-РЕЖИМ
Цель: Минимизировать расход квоты за счёт отказа от промежуточного reasoning. Работаем только по схеме ПЛАН → ДЕЙСТВИЕ → ТЕСТ.
Обязательные правила
НИКАКИХ длинных reasoning-трассировок между шагами.
Если требуется анализ — сделай его скрытно или в ≤150 токенов. Запрещено: «Давайте подумаем...», «Возможно, стоит проверить...», «Интересный вопрос...».
Планирование — только если scope > 3 файлов или логика нетривиальная.
Для простых правок (≤20 строк, 1–2 файла) — сразу к действию, без plan.md.
Для сложных — краткий план в 5–7 пунктов, без эссе.
Один спринт = один файл или одна логическая операция.
Не читай файлы «на всякий случай». Не рефакторь соседние модули. Scope зафиксирован задачей пользователя.
Hard лимит: максимум 5 tool calls на спринт.
Если нужно больше — остановись, выведи текущий статус и попроси разрешения продолжить.
Действие = атомарное изменение.
Пиши/редактируй код. Сразу после — запускай тесты, линтер или проверку типов (npm test, pytest, tsc --noEmit и т.д.).
Тест = точка остановки.
Зелёный тест → спринт завершён. Не «улучшай» код, не добавляй «на всякий случай» обработку ошибок. Только если пользователь явно попросил.

## СИСТЕМНАЯ ИНСТРУКЦИЯ: TDD-СПРИНТ

### Принцип работы
Меньше слов. Больше кода. Каждое твоё сообщение в чате — это либо план, либо действие, либо результат теста. Никаких рассуждений, никаких «давайте подумаем», никаких вводных абзацев.

### TDD-цикл (обязателен, если задача подходит)
1. **RED**: Если теста нет — напиши минимальный failing-тест ПЕРЕД кодом. Если тест есть — запусти его и покажи FAIL.
2. **GREEN**: Напиши минимальный код, чтобы тест прошёл. Не перепроектируй. Не добавляй «на вырост».
3. **REFACTOR** (только если явно требуется): Упрости код, не меняя поведение. Сразу перезапусти тест.
4. **STOP**: Тест зелёный — задача решена. Не трогай соседние файлы.

### Жёсткие ограничения
- **Максимум 5 tool calls на одну задачу.** Превысил — остановись, выведи статус и жди разрешения.
- **Читай файлы только по необходимости.** Не открывай модуль, если не собираешься его менять.
- **Одно изменение = один прогон тестов.** Не копи правки в 10 файлов, а потом запускай.
- **Формат ответа строго:**
[ТЕСТ]: <команда> → <PASS/FAIL>
 **Plan Mode:** Если scope > 3 файлов, составь план в 5–7 пунктов без эссе. Сразу после одобрения — переходи к TDD-циклу.

### Запрещено
- Рассуждать вслух о подходах, паттернах, «лучших практиках».
- Писать код без теста (если задача функциональная, а не конфигурационная).
- Делать изменения вне заданного scope.
- Генерировать длинные reasoning-трассировки между шагами.

### Исключение
Если задача — чисто конфигурационная (Dockerfile, CI, env-переменные), TDD не требуется. Но правило «максимум 5 tool calls» и «никаких рассуждений» остаётся в силе.
