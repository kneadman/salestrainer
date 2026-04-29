# Sales Trainer MVP

CLI MVP for an interactive sales training simulator. A manager writes messages, the system simulates a cold B2B client, and the application owns all session state.

## Current MVP scope

- CLI chat only
- Fake LLM is the default working flow
- Session state stored in app-managed repository
- Redis docker setup included
- Domain validation via Pydantic v2

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

Prompt ownership:

- `app/prompts/client_simulator.md` is a local reference prompt used for documentation and prompt iteration
- The `yandex_compatible` runtime path currently uses the configured Yandex AI Studio agent via `YANDEX_AGENT_ID`
- If you update local prompt text, it does not automatically change the remote runtime agent behavior

## Run tests

```bash
pytest
```

Start local Redis for integration-style repository checks:

```bash
docker compose up -d
```

## MVP limitations

- Real Yandex/OpenAI API is not connected to the working flow
- Yandex adapter now follows the AI Studio `OpenAI(...).responses.create(...)` contract and is covered by mocked request/response tests, but is still not verified here against a live cloud account
- The local `client_simulator.md` file is not injected into Yandex runtime requests; the remote agent remains the runtime prompt source for that backend
- CLI still uses a simple terminal flow
- Reports are rule-based, not judge-model based
- Session resume across process restarts requires Redis; in-memory mode is process-local and does not survive restarts

## Next step roadmap

1. Add real LLM client behind the same protocol
2. Add JSON schema enforcement and retry on invalid provider output
3. Expose the same application services through API DTOs
4. Add public projections for future frontend
