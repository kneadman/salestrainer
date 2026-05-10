# Sales Trainer MVP

CLI/API MVP for an interactive sales training simulator. A manager writes messages, the system simulates a hidden B2B client, and the application owns all session state.

## Agent-facing code reference

Detailed agent-facing documentation is stored in `docs/agent-reference/`.
Start from `docs/agent-reference/README.md`.

## Current MVP scope

- CLI chat plus FastAPI API
- Fake LLM is the default working flow
- Session state stored in app-managed repository
- Redis docker setup included
- PostgreSQL stores identity and client access data; Alembic manages relational migrations
- PostgreSQL stores persistent training history, reports, and usage events for authenticated API sessions
- Internal admin backend foundation exists under `/api/internal/*`
- Domain validation via Pydantic v2
- The client profile is generated at session start and remains hidden during the training

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

## Run CLI

```bash
python -m app.cli.main
```

Available commands:

- `/start`
- `/resume`
- `/scenarios`
- `/state`
- `/history`
- `/finish`
- `/help`
- `/exit`

On startup, the CLI stays idle until you explicitly run `/start` or `/resume <session_id>`.

Core training loop:

- `/start` creates a session with the default `generic_b2b_first_contact` scenario
- The trainer generates a hidden client profile at random
- The manager does not choose a persona and does not see the client's exact role up front
- The goal is discovery-first: identify role, authority, pain, constraints, and decision criteria before pushing a next step
- The hidden profile is revealed only in the final report after `/finish`

Enable CLI debug output:

```bash
set DEBUG_CLI=true
python -m app.cli.main
```

Choose LLM backend:

```bash
set LLM_BACKEND=fake
python -m app.cli.main
```

Deterministic persona generation for tests or debug:

```bash
set PERSONA_RANDOM_SEED=42
python -m app.cli.main
```

Default scenario selection:

```bash
set DEFAULT_TRAINING_SCENARIO_ID=generic_b2b_first_contact
python -m app.cli.main
```

## Admin CLI (internal)

Internal admin CLI for manual management of clients, users, and training configs.

Before running commands, ensure migrations are applied (`python -m alembic upgrade head`) and `DATABASE_URL` points to the target PostgreSQL.

Create client:

```bash
python -m app.admin.cli create-client --name "ООО Ромашка" --slug romashka
```

Create user (stores only password hash):

```bash
python -m app.admin.cli create-user --client romashka --email manager@romashka.ru --password "temporary-password"
```

Create client training config from persona policy JSON:

```bash
python -m app.admin.cli create-config \
  --client romashka \
  --name "Бухгалтерский аутсорсинг" \
  --product-line accounting_outsourcing \
  --scenario generic_b2b_first_contact \
  --persona-policy-file configs/romashka-accounting.json
```

Assign config to user (`--default` makes it default for that user):

```bash
python -m app.admin.cli assign-config --email manager@romashka.ru --config "Бухгалтерский аутсорсинг" --default
```

Reset password (updates `password_hash` and sets `must_change_password=true`):

```bash
python -m app.admin.cli reset-password --email manager@romashka.ru --password "new-temporary-password"
```

Disable user (sets `is_active=false`):

```bash
python -m app.admin.cli disable-user --email manager@romashka.ru
```

## Roles and internal admin API

User roles are centralized in `app.identity.roles`:

- `internal_admin`: platform owner / internal operator
- `client_lead`: client-side lead
- `client_manager`: client-side manager
- legacy `client_user` is normalized to `client_manager` for backward compatibility

Internal admin API endpoints are mounted under `/api/internal/*` and require an authenticated `internal_admin` session plus CSRF for mutating requests. Client roles receive `403`.

Internal admin foundation includes:

- organizations: list/create/detail/update/disable/enable via `/api/internal/organizations`
- organization users: create `client_lead` / `client_manager`, update, disable/enable, reset temporary password
- training configs: create/update/disable/enable and assign/unassign/make-default per user
- legacy LLM provider config endpoints remain available for future/internal use, but are not part of the MVP training flow
- audit log: `GET /api/internal/audit-log`

Training runtime sessions still use Redis and the existing `/api/sessions/*` flow. Billing is not implemented.

## Internal Admin UI

The internal platform owner cabinet is available at:

```text
/admin
```

Access rules:

- unauthenticated users are redirected to `/login`;
- `internal_admin` can open the admin cabinet;
- `client_lead` and `client_manager` see a no-access screen and can return to `/app`;
- admin requests use the existing HttpOnly auth cookie and CSRF token flow.

Admin UI sections:

- Dashboard: organization totals, users/config counts, usage totals, latest audit events;
- Organizations: list/search/create/edit/enable/disable organizations;
- Organization detail: overview, users, training configs, history, usage, audit;
- Users: create/update users, reset temporary passwords, enable/disable, assign/default/unassign training configs;
- Training Configs: create/update/enable/disable configs with client-side JSON validation and `persona_generation_context`;
- Training History: persistent history list and public-safe session detail;
- Usage Analytics: basic usage summary from persistent history;
- Audit Log: filterable audit events with compact JSON payload display.

Security notes:

- global Yandex API keys, folder IDs, and agent IDs are configured through `.env`, not through the admin UI;
- passwords are not stored in localStorage/sessionStorage and reset fields are cleared after success;
- hidden persona snapshots, raw LLM payloads, raw LLM responses, and secrets are not rendered in admin history views.

## Persistent Training History

Active training state and long-term history have separate owners:

- Redis stores active runtime `TrainingSessionState` while a dialog is in progress.
- PostgreSQL stores durable history, reports, usage events, and analytics inputs.

The authenticated `/api/sessions/*` flow now writes persistent history after the runtime operation succeeds:

- `POST /api/sessions` creates a `training_sessions` row and `session_started` usage event.
- `POST /api/sessions/{session_id}/messages` appends `training_turns`, updates session counters/snapshots, and writes `turn_processed`.
- `POST /api/sessions/{session_id}/finish` marks the session finished, stores `training_reports`, and writes `session_finished` plus `report_generated`.
- `GET /api/sessions/{session_id}` and resume calls may write view/resume usage events.

New tables:

- `training_sessions`: durable session metadata, public brief, summary, server-side persona and state snapshots.
- `training_turns`: durable turn history with manager/client messages, interest/stage transition, public-safe state snapshots, and evaluation snapshot.
- `training_reports`: saved final report text per session.
- `usage_events`: minimal event stream for future analytics.

Client-facing history endpoints:

- `GET /api/history/sessions`
- `GET /api/history/sessions/{session_id}`
- `GET /api/history/sessions/{session_id}/report`

Internal admin history endpoints:

- `GET /api/internal/organizations/{organization_id}/history/sessions`
- `GET /api/internal/organizations/{organization_id}/usage-summary`
- `GET /api/internal/users/{user_id}/history/sessions`

Access rules:

- `client_manager` sees only their own history.
- `client_lead` sees sessions for users in the same client account.
- `internal_admin` uses `/api/internal/*` history and usage endpoints.
- Client-facing history DTOs do not expose `persona_snapshot`, raw LLM payloads, raw LLM responses, API keys, or hidden persona fields.

Limitations:

- History starts only for sessions created after the migration is applied.
- Old Redis-only sessions are not backfilled.
- Analytics is a basic aggregation API, not a dashboard.
- Hidden snapshots can be stored server-side for future internal/admin use, but are not returned by client-facing endpoints.
- If a persistent history turn write fails after Redis state is updated, the API returns a controlled `500` and logs a critical consistency error; automated retry/reconciliation is a later step.

## Password change flow

`/auth/login` and `/auth/me` now include `user.must_change_password`. A user with a temporary password can call:

```http
POST /auth/change-password
```

```json
{
  "current_password": "temporary-password",
  "new_password": "new-password"
}
```

The endpoint requires auth cookie and CSRF token, verifies the current password, stores only an Argon2id hash, clears `must_change_password`, and writes an audit record.

## MVP LLM model

MVP runtime no longer depends on organization-level `llm_provider_config_id`.

- One global `YANDEX_API_KEY` is configured in `.env`.
- One global persona generator agent is configured in `.env`.
- One global dialogue agent is configured in `.env`.
- `persona_generation_context` is stored on `client_training_configs` and edited only by `internal_admin`.
- Persona and dialogue master prompts plus JSON templates live inside Yandex Agents, not in the service database.
- Backend still validates provider JSON through Pydantic and business rules before it touches runtime state.

Recommended environment variables:

```bash
set LLM_BACKEND=yandex_compatible
set YANDEX_API_KEY=...
set YANDEX_BASE_URL=https://ai.api.cloud.yandex.net/v1
set YANDEX_PERSONA_FOLDER_ID=...
set YANDEX_PERSONA_AGENT_ID=...
set YANDEX_DIALOGUE_FOLDER_ID=...
set YANDEX_DIALOGUE_AGENT_ID=...
```

Legacy fallback variables are still supported:

```bash
set YANDEX_FOLDER_ID=...
set YANDEX_AGENT_ID=...
```

`llm_provider_configs` and `/api/internal/*/llm-provider-configs` remain in the backend as legacy/future-enterprise groundwork, but the MVP runtime and primary admin UI do not use them.

## LLM Persona Generation

Authenticated API session creation separates persona generation from dialogue simulation:

- Persona Generator LLM creates the hidden `PersonaProfile` once at session start from the user's default `client_training_config`.
- Dialogue Simulator LLM continues to answer manager turns from the saved hidden profile and runtime state.
- Redis stores the active `TrainingSessionState`, including the hidden persona.
- PostgreSQL history stores server-side snapshots after the API session is created.

Generation input is normalized into `PersonaGenerationInput`:

- scenario;
- training config name;
- `persona_generation_context` business context;
- free-form `persona_policy`;
- optional organization context, target action, allowed roles/product lines, training goal, difficulty, seed, and constraints.

Generation output must validate as `PersonaGenerationOutput` and contain a Pydantic-valid `PersonaProfile`. Provider responses are parsed as structured JSON; invalid output is retried by the provider client and then fails the API request unless local fallback is explicitly allowed.

Provider behavior:

- `fake` provider uses the legacy Python `PersonaGenerator`.
- `yandex_compatible` uses the global persona agent from `.env`.
- If `persona_generation_context` is empty, local mode can fall back to the legacy Python generator; production-like mode returns a controlled configuration error.
- API keys are read from environment settings, are never logged in full, and are never returned.

Security notes:

- client-facing session and history endpoints still do not expose the hidden persona before the final report flow allows it;
- raw persona-generation prompts, raw provider payloads, raw provider responses, and secrets are not written to client endpoints or usage events;
- debug payload logging remains gated by `DEBUG_LLM_PAYLOAD`.

Set `SECRET_ENCRYPTION_KEY` for application-level secret encryption:

```bash
set SECRET_ENCRYPTION_KEY=replace-with-random-32-plus-character-secret
```

In `APP_ENV=local`, a development fallback key is available for local tests and demos. Outside local environment, operations that encrypt/decrypt provider secrets require `SECRET_ENCRYPTION_KEY`.

Dialogue runtime uses the same global API key and base URL, plus dialogue-specific routing:

```bash
set LLM_BACKEND=yandex_compatible
set YANDEX_API_KEY=...
set YANDEX_DIALOGUE_FOLDER_ID=...
set YANDEX_DIALOGUE_AGENT_ID=...
python -m app.cli.main
```

Fallback policy:

- `APP_ENV=local` allows fallback to `FakeLLMClient` and `InMemorySessionRepository` even if the explicit allow-flags are `false`
- `APP_ENV=staging` or `APP_ENV=prod` should usually run with `ALLOW_FAKE_LLM_FALLBACK=false` and `ALLOW_IN_MEMORY_REPOSITORY=false`
- In those environments, incomplete Yandex config or unavailable Redis now fail explicitly during startup instead of silently degrading

LLM logging:

- INFO logs contain only sanitized metadata
- Full request payload logging is disabled by default and can be enabled with `DEBUG_LLM_PAYLOAD=true`
- API keys are never logged in full

Public vs hidden state:

- Public CLI/API state exposes only a safe brief, current stage, interest, visible objections, discovered pains, and buying signals
- Hidden role, authority level, latent pains, constraints, motivations, and internal behavior model stay server-side during the session
- `FakeLLMClient` and real LLM adapters receive the hidden profile so the client behavior stays consistent

Prompt ownership:

- Master prompts for persona generation and dialogue live in Yandex Agents and are edited in Yandex, not in this service.
- JSON schema/templates for structured responses are configured in Yandex Agent plus validated again by this backend.
- `app/prompts/client_simulator.md` and `app/prompts/persona_generator.md` are local reference prompts for documentation and prompt iteration only.
- The MVP service stores only `persona_generation_context` as client business context on a training config.
- Client/training config records do not store API keys, folder IDs, agent IDs, master prompts, or JSON templates.

Example `persona_generation_context`:

```text
Client sells accounting outsourcing and outsourced CFO services to Russian B2B companies with 20-200 employees.
Target decision-makers are owners, CEOs, CFOs, and managing partners.
Typical pains: late management reporting, unclear cash gaps, tax risks, overloaded in-house accountant.
Typical objections: already have an accountant, do not want to share financial data, had bad vendor experience, price concerns.
Decision criteria: reliability, relevant cases, clear onboarding, transparent reporting, ability to work with 1C and primary documents.
Training goal: manager should discover role, current accounting process, pain, decision criteria, and earn a relevant next step.
```

## Judgement Layer contract

- Judge runs only after finish.
- PR1 adds the strict Pydantic contract, PR2 adds `FakeJudgeClient` plus `JudgementService`, PR3 adds the reference judge prompt plus `StructuredJudgeClient`, PR4 wires `build_judge_client(settings)` into runtime, PR5 makes judge payload generation fail-open with minimal `report_payload` support, and PR6 adds typed frontend bento report rendering plus basic analytics from saved judge payloads.
- Runtime dialogue flow does not change.
- Judge still runs only after finish/report generation.
- `JudgeSessionOutput` is persisted into `training_reports.report_payload`.
- `GET /report` reuses saved `report_payload` when available instead of regenerating it.
- If judge payload generation fails, `/finish` and `/report` still return the plain text report instead of failing the core flow.
- API finish/report responses and history report DTOs now include optional `report_payload`.
- Frontend opens the structured bento report in a modal after session finish. A compact `Отчёт` button is shown near the chat for finished sessions and reopens the saved report. The legacy plain text report is used only as a modal fallback when structured payload is unavailable or invalid.
- Client/team analytics can optionally include basic aggregates from saved valid `JudgeSessionOutput` payloads such as average judge score and weakest skill.
- Judge uses shared `YANDEX_API_KEY` and `YANDEX_BASE_URL`.
- Optional judge routing env vars:
  - `YANDEX_JUDGE_FOLDER_ID`
  - `YANDEX_JUDGE_AGENT_ID`
- User-facing judge text should be Russian by default unless the whole input session is clearly in another language.

## Demo run checklist

1. Start the production-like local stack:

```bash
docker compose up --build
```

2. Migrations are run by the `migrate` compose service. For manual local backend runs, use:

```bash
python -m alembic upgrade head
```

3. Create the first internal admin:

```bash
python -m app.admin.cli create-internal-admin --client-name "Platform" --client-slug platform --email admin@example.com --password "temporary-password"
```

4. Open `http://localhost:8080/login`, sign in, then open `/admin`.
5. Create an organization.
6. Create a training config with name, scenario, limits, and `persona_generation_context`.
7. Create a client manager or lead user.
8. Assign the training config to the user and mark it as default.
9. Sign in as the client user.
10. Open `/app/trainer`.
11. Start a training and send at least one manager message.
12. Finish the session.
13. Open `/app/history`, the saved report, and `/app/analytics`.

Demo notes:

- Authenticated session creation uses the global persona agent from `.env`.
- Runtime dialogue turns use the global dialogue agent from `.env`.
- Legacy organization-level LLM provider configs are not part of the MVP demo flow.
- Landing form submissions are persisted in `landing_leads`.
- `/app/balance` is a usage placeholder, not billing or payment processing.

If real Yandex credentials are unavailable, keep `APP_ENV=local` and use fake/local fallback for a presentation of the product flow. For staging/prod, configure real secrets and disable fake fallback.

## Run tests

```bash
pytest
```

## Local infrastructure

Start Redis and PostgreSQL for local backend development:

```bash
docker compose up -d redis postgres
```

Default local URLs:

```text
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/sales_trainer
```

Apply migrations:

```bash
python -m alembic upgrade head
```

## Frontend GUI

Minimal React/Vite web UI lives in `frontend/`.

Backend:

```bash
python -m alembic upgrade head
python -m uvicorn app.api.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

The Vite dev server proxies API requests to `http://localhost:8000`, so the frontend uses relative calls such as `/auth/login`, `/auth/csrf`, and `/api/sessions`.

Production serving through FastAPI:

```bash
cd frontend
npm install
npm run build
cd ..
python -m uvicorn app.api.main:app
```

Open:

```text
http://localhost:8000/login
```

Current client access flow:

- `/auth/login`, `/auth/logout`, `/auth/me`, and `/auth/csrf` implement the browser login flow
- `/auth/change-password` lets authenticated users replace temporary passwords and clears `must_change_password`
- auth uses an HttpOnly session cookie; CSRF tokens are sent with mutating requests through `X-CSRF-Token`
- `/app` is the client cabinet dashboard
- `/app/trainer` contains the Redis-backed active training flow
- `/api/sessions` requires an authenticated user
- `POST /api/sessions` creates a training session from the current user's default training config
- `training_session_ownership` is used to check access to session endpoints
- PostgreSQL stores identity, access data, persistent training history, reports, and usage events
- Redis stores runtime training sessions
- `/admin` serves the internal admin UI for `internal_admin` users

## Client Cabinet

The client cabinet is mounted under `/app` and is separate from the internal admin cabinet.

Routes:

- `/app`: client dashboard with personal overview and lead team summary when available;
- `/app/trainer`: active training simulator;
- `/app/history`: role-scoped persistent training history;
- `/app/history/{session_id}`: public-safe session detail and saved report;
- `/app/analytics`: personal analytics;
- `/app/team`: same-organization manager list for `client_lead`;
- `/app/team/{user_id}`: manager analytics card for `client_lead`;
- `/app/team-analytics`: organization analytics for `client_lead`;
- `/app/balance`: usage and billing placeholder without payment processing;
- `/app/settings`: profile and password change form.

Role rules:

- `client_manager` sees only personal navigation and personal history/analytics.
- `client_lead` sees personal sections plus team and team analytics for the same organization.
- `client_manager` cannot use `/app/team` or `/app/team-analytics`.
- Team APIs never use `/api/internal/*`; they use client-facing `/api/team/*` endpoints protected by `client_lead`.

Client-facing analytics endpoints:

- `GET /api/client/analytics/me`
- `GET /api/team/users`
- `GET /api/team/usage-summary`
- `GET /api/team/users/{user_id}/analytics`
- `GET /api/team/users/{user_id}/history/sessions`

Limitations:

- Balance is usage-oriented only; real billing, invoices, and payment forms are not implemented.
- Detailed skill/evaluation aggregates are shown as an empty state until backend exposes safe aggregates.
- Analytics appears only after persistent history rows exist.
- `/api/leads` uses persistence, payload limits, attribution whitelisting, and a honeypot, but full rate limiting and CRM integration are not implemented yet.

## Run with Docker

Production-like local stack:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8080
```

Notes:

- `frontend` is built once and served by `nginx`
- `migrate` runs `python -m alembic upgrade head` before `backend` starts
- `nginx` proxies `/api/*` and `/auth/*` to the internal `backend:8000` service
- `backend` connects to Redis through `redis://redis:6379/0`
- `backend` connects to PostgreSQL through `postgresql+psycopg://postgres:postgres@postgres:5432/sales_trainer`
- `backend` image now includes `ffmpeg`/`ffprobe`, a built-in `whisper-cli`, and the default `ggml-base.bin` model, so browser-audio duration probing, WAV preprocessing, and `whisper.cpp` STT can run in-container without manual VPS setup
- only port `8080` is exposed to the host

Smoke checks through nginx:

```bash
curl -i http://localhost:8080/auth/me
curl -i http://localhost:8080/auth/csrf
curl -i http://localhost:8080/api/health
```

STT container smoke test:

```bash
docker compose build --no-cache backend
docker compose up -d backend
docker compose exec backend bash -lc 'ldd /usr/local/bin/whisper-cli | grep "not found" || true'
docker compose exec backend bash -lc 'ffmpeg -f lavfi -i sine=frequency=1000:duration=2 -ac 1 -ar 16000 /tmp/test.wav -y'
docker compose exec backend bash -lc '"$STT_WHISPER_CPP_BINARY" -m "$STT_MODEL_PATH" -f /tmp/test.wav -l ru -otxt -of /tmp/test-out'
docker compose exec backend cat /tmp/test-out.txt
```

Expected results:

- `/auth/me` returns a `401` JSON response, not React `index.html`
- `/auth/csrf` returns `200` JSON with `csrf_token`
- `/api/health` returns `200 {"status":"ok"}`

## API session creation

The main creation flow no longer requires `persona_id`.

Minimal request:

```json
{}
```

Explicit scenario:

```json
{
  "scenario_id": "generic_b2b_first_contact"
}
```

Debug-compatible preset mode still works:

```json
{
  "scenario_id": "sales_audit_cold_outreach",
  "persona_id": "owner"
}
```

## Legacy Hidden Client Generation

The fallback/debug generator lives in `app/domain/persona_generation.py`.

Each generated client profile includes:

- role
- industry
- company_size
- authority_level
- behavior_model
- current_business_context
- latent_pains
- typical_objections
- buying_motivation
- decision_criteria
- hidden_constraints
- communication_style
- starting_interest / initial_openness
- price_sensitivity
- urgency
- trust_baseline

For production client API sessions, prefer configuring `persona_generation_context` plus optional `persona_policy`. To improve the fallback path, extend the role templates in that module with new combinations of role, pains, context, and constraints.

## MVP limitations

- A live Yandex cloud smoke test is not part of this iteration.
- Real Yandex/OpenAI API is not connected to the working flow
- Yandex adapter now follows the AI Studio `OpenAI(...).responses.create(...)` contract and is covered by mocked request/response tests, but is still not verified here against a live cloud account
- The local `client_simulator.md` file is not injected into Yandex runtime requests; the remote dialogue agent remains the runtime prompt source
- Legacy `llm_provider_configs` still exist in the backend, but the primary MVP flow does not use them
- CLI still uses a simple terminal flow
- Reports and evaluator scores are rule-based, not judge-model based
- Session resume across process restarts requires Redis; in-memory mode is process-local and does not survive restarts
- Persistent history is written by the authenticated API flow; CLI local training remains runtime-only.

## Next step roadmap

1. Client/Admin analytics API hardening with focused frontend tests and richer filtering
2. Prompt examples, stricter startup validation, and wider regression coverage for hidden-field safety
3. Real billing/limits model for organization usage
4. Provider retry/backoff and prompt/schema versioning
