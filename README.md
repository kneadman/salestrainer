# Sales Trainer MVP

CLI/API MVP for an interactive sales training simulator. A manager writes messages, the system simulates a hidden B2B client, and the application owns all session state.

## Current MVP scope

- CLI chat plus FastAPI API
- Fake LLM is the default working flow
- Session state stored in app-managed repository
- Redis docker setup included
- PostgreSQL stores identity and client access data; Alembic manages relational migrations
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

Before running commands, ensure migrations are applied (`alembic upgrade head`) and `DATABASE_URL` points to the target PostgreSQL.

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

Optional experimental provider path:

```bash
set LLM_BACKEND=yandex_compatible
set YANDEX_API_KEY=...
set YANDEX_FOLDER_ID=...
set YANDEX_AGENT_ID=fvtpps65vhjr2j1qul0a
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

- `app/prompts/client_simulator.md` is a local reference prompt used for documentation and prompt iteration
- The `yandex_compatible` runtime path currently uses the configured Yandex AI Studio agent via `YANDEX_AGENT_ID`
- If you update local prompt text, it does not automatically change the remote runtime agent behavior

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
alembic upgrade head
```

## Frontend GUI

Minimal React/Vite web UI lives in `frontend/`.

Backend:

```bash
alembic upgrade head
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
- auth uses an HttpOnly session cookie; CSRF tokens are sent with mutating requests through `X-CSRF-Token`
- `/api/sessions` requires an authenticated user
- `POST /api/sessions` creates a training session from the current user's default training config
- `training_session_ownership` is used to check access to session endpoints
- PostgreSQL stores identity and access data
- Redis stores runtime training sessions

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
- `migrate` runs `alembic upgrade head` before `backend` starts
- `nginx` proxies `/api/*` and `/auth/*` to the internal `backend:8000` service
- `backend` connects to Redis through `redis://redis:6379/0`
- `backend` connects to PostgreSQL through `postgresql+psycopg://postgres:postgres@postgres:5432/sales_trainer`
- only port `8080` is exposed to the host

Smoke checks through nginx:

```bash
curl -i http://localhost:8080/auth/me
curl -i http://localhost:8080/auth/csrf
curl -i http://localhost:8080/api/health
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

## Hidden client generation

The generator lives in `app/domain/persona_generation.py`.

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

To add more client variants, extend the role templates in that module with new combinations of role, pains, context, and constraints.

## MVP limitations

- Real Yandex/OpenAI API is not connected to the working flow
- Yandex adapter now follows the AI Studio `OpenAI(...).responses.create(...)` contract and is covered by mocked request/response tests, but is still not verified here against a live cloud account
- The local `client_simulator.md` file is not injected into Yandex runtime requests; the remote agent remains the runtime prompt source for that backend
- CLI still uses a simple terminal flow
- Reports and evaluator scores are rule-based, not judge-model based
- Session resume across process restarts requires Redis; in-memory mode is process-local and does not survive restarts

## Next step roadmap

1. Add real LLM client behind the same protocol
2. Add JSON schema enforcement and retry on invalid provider output
3. Expose the same application services through API DTOs
4. Add public projections for future frontend
