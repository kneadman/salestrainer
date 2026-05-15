# Sales Trainer MVP

Sales Trainer MVP — тренажёр B2B-продаж для менеджеров и руководителей команд. Менеджер ведёт диалог с симулированным клиентом, а система оценивает ход разговора, обновляет интерес клиента, сохраняет историю и формирует отчёт.

Главный архитектурный принцип: backend владеет состоянием. LLM не хранит сессию и не принимает бизнес-решения; она возвращает следующую реплику клиента, ограниченный `state_patch` и новые публично раскрытые `revealed_facts`, которые backend валидирует и мержит.

## Возможности

- Клиентский кабинет `/app` с тренажёром, историей, отчётами, персональной и командной аналитикой.
- Внутренний админский кабинет `/admin` для организаций, пользователей, training configs, истории, usage summary и audit log.
- FastAPI backend, React 18 + TypeScript + Vite frontend.
- Redis для активного runtime-состояния тренировки.
- PostgreSQL для пользователей, доступов, training configs, durable history, отчётов, usage events и audit log.
- Cookie auth через HttpOnly session cookie и CSRF для mutating-запросов.
- Роли `internal_admin`, `client_lead`, `client_manager`; legacy `client_user` нормализуется в `client_manager`.
- Yandex/OpenAI-compatible LLM adapters для persona generation, dialogue и judge.
- Fake/local LLM fallback для разработки и демо.
- Voice input MVP: браузерная запись голоса, batch STT через `/api/speech/transcribe`, вставка текста в composer без auto-send.
- Public landing `/` и lead form `/api/leads`.

## Стек

- Python 3.13+, FastAPI, Pydantic v2, SQLAlchemy, Alembic.
- PostgreSQL, Redis.
- React 18, TypeScript, Vite, nginx.
- Yandex-compatible LLM agents; fake fallback только для local/dev/demo.

## Архитектура

Поток активной тренировки:

```text
frontend / API / CLI
  -> application services
  -> domain models and rules
  -> infrastructure adapters
  -> Redis runtime state
  -> PostgreSQL durable history
```

Важные границы:

- Domain layer не импортирует FastAPI, Redis, SQLAlchemy или frontend-типы.
- Redis хранит активную runtime-сессию.
- PostgreSQL хранит durable history, auth, analytics и audit.
- `StatePatch` — предложение модели, а не источник истины.
- `interest_score` и stage transitions контролируются backend.
- Hidden persona не попадает в client-facing API, frontend, browser state или обычные логи.
- Блок «Факты и боли» строится только из `revealed_facts`; legacy `discovered_*` остаются для внутренней логики стадий, отчётов и совместимости.

## Документация для разработки

Подробная карта кода и правил лежит в:

```text
docs/agent-reference/README.md
```

Полезные разделы:

- `ARCHITECTURE.md` — слои и runtime flow.
- `API_REFERENCE.md` — основные endpoints.
- `DATA_AND_STATE.md` — Redis/PostgreSQL и DTO boundaries.
- `SECURITY_AND_AUTH.md` — auth, CSRF, роли, audit.
- `LLM_AND_PROMPTS.md` — persona/dialogue/judge contracts.
- `STT.md` — голосовой ввод.
- `DEVOPS.md` — Docker, nginx, env и smoke checks.

## Быстрый локальный запуск

Требования:

- Python 3.13+.
- Node.js для frontend.
- Docker, если Redis/PostgreSQL запускаются через compose.

Backend:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .
```

Инфраструктура и миграции:

```bash
docker compose up -d redis postgres
python -m alembic upgrade head
```

Backend API:

```bash
python -m uvicorn app.api.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Открыть:

```text
http://localhost:5173
```

Vite dev server использует относительные API-пути и проксирует запросы на backend.

## Docker stack

Production-like локальный запуск:

```bash
docker compose up --build
```

Открыть:

```text
http://localhost:8080
```

Compose поднимает `postgres`, `redis`, `migrate`, `backend` и `frontend` на nginx. `migrate` применяет Alembic migrations до старта backend. Nginx проксирует `/api/*` и `/auth/*` в backend, а frontend отдаёт как SPA.

Smoke checks:

```bash
curl -i http://localhost:8080/auth/me
curl -i http://localhost:8080/auth/csrf
curl -i http://localhost:8080/api/health
```

Ожидаемо:

- `/auth/me` без cookie возвращает `401` JSON.
- `/auth/csrf` возвращает `200` JSON с `csrf_token`.
- `/api/health` возвращает `200 {"status":"ok"}`.

## Переменные окружения

Настройки читаются из `.env` через `app.infrastructure.config.Settings`. Безопасный шаблон лежит в `.env.example`.

Ключевые группы:

- Redis/PostgreSQL: `REDIS_URL`, `DATABASE_URL`.
- Runtime: `APP_ENV`, `SESSION_TTL_SECONDS`, `DEFAULT_TRAINING_SCENARIO_ID`.
- Auth/cookies: `AUTH_SESSION_TTL_SECONDS`, `AUTH_COOKIE_SECURE`, `AUTH_COOKIE_SAMESITE`, `CSRF_TOKEN_TTL_SECONDS`.
- Rate limits/proxy: `LOGIN_RATE_LIMIT_ATTEMPTS`, `LEAD_RATE_LIMIT_ATTEMPTS`, `TRUSTED_PROXY_IPS`.
- LLM: `LLM_BACKEND`, `ALLOW_FAKE_LLM_FALLBACK`, `YANDEX_API_KEY`, `YANDEX_BASE_URL`, `YANDEX_PERSONA_*`, `YANDEX_DIALOGUE_*`, `YANDEX_JUDGE_*`.
- STT: `STT_ENABLED`, `STT_BACKEND`, `STT_WHISPER_CPP_BINARY`, `STT_MODEL_PATH`, `STT_RATE_LIMIT_ATTEMPTS`, `STT_GLOBAL_RATE_LIMIT_ATTEMPTS`.

`.env` не должен попадать в Git.

## Auth и роли

Browser auth использует HttpOnly session cookie. Mutating-запросы в `/auth/*`, `/api/*` и `/api/internal/*` требуют CSRF header `X-CSRF-Token`, кроме явно открытых endpoints вроде `/auth/login` и `/api/leads`.

Роли:

- `internal_admin` — внутренний оператор платформы, доступ к `/admin` и `/api/internal/*`.
- `client_lead` — руководитель команды клиента, видит свои данные и командные разделы организации.
- `client_manager` — менеджер, видит только свои тренировки, историю и аналитику.

Пароли хэшируются Argon2id. Постоянный пароль должен быть длиной 8–256 символов и состоять только из латинских букв и цифр. Temporary/reset passwords переводят пользователя в `must_change_password=true`.

## Клиентский кабинет

Кабинет клиента находится под `/app`.

Основные маршруты:

- `/app` — dashboard.
- `/app/trainer` — активная тренировка.
- `/app/history` — история тренировок.
- `/app/history/{session_id}` — детали сессии и отчёт.
- `/app/analytics` — персональная аналитика.
- `/app/team` — список пользователей команды для `client_lead`.
- `/app/team/{user_id}` — аналитика и история конкретного пользователя для `client_lead`.
- `/app/team-analytics` — командная аналитика и рейтинг менеджеров.
- `/app/settings` — профиль и смена пароля.

Клиентский UI не вызывает `/api/internal/*`; для team-разделов используются client-facing endpoints `/api/team/*`.

## Внутренний админский кабинет

Админка находится под:

```text
/admin
```

Доступ есть только у `internal_admin`.

Основные возможности:

- управление организациями;
- управление пользователями организаций;
- reset/disable/enable пользователей;
- управление training configs;
- история и usage summary по организациям;
- audit log;
- permalink user analytics;
- backend-groundwork для legacy/future LLM provider config API.

Админка не показывает полные API keys, raw LLM payloads, raw LLM responses, hidden persona snapshots или временные пароли после отправки.

## Training flow

Активная тренировка создаётся через:

```http
POST /api/sessions
```

Для обычного client user backend:

1. Проверяет default training config пользователя.
2. Генерирует скрытую `PersonaProfile` через `PersonaGenerationService`.
3. Создаёт Redis runtime-сессию.
4. Создаёт ownership-запись.
5. Пишет durable history row и usage event в PostgreSQL.
6. Возвращает public-safe DTO без hidden persona.

Сообщение менеджера:

```http
POST /api/sessions/{session_id}/messages
```

Поддерживается optional `idempotency_key`:

- тот же ключ + тот же текст возвращает сохранённый public response;
- тот же ключ + другой текст возвращает `409`;
- frontend переиспользует ключ при retry одного и того же сообщения.

Если Redis обновился, а запись turn history в PostgreSQL не прошла, runtime-сессия помечается как pending retry. Следующее resume/send/finish сначала пытается восстановить history gap.

Завершение:

```http
POST /api/sessions/{session_id}/finish
GET /api/sessions/{session_id}/report
```

Judge payload строится после finish. Если judge падает, plain text report остаётся fallback-контрактом.

## Публичные факты и скрытая persona

Во время активной тренировки клиентскому API и frontend нельзя раскрывать:

- полный `PersonaProfile`;
- hidden display name;
- скрытую роль, если она не была раскрыта;
- `authority_level`, если полномочия не были раскрыты;
- latent pains и hidden constraints до discovery;
- raw LLM payloads/responses;
- provider/internal notes.

`revealed_facts` — единственный источник для UI-блока «Факты и боли». Dialogue LLM возвращает только новые факты текущего ответа клиента, backend фильтрует technical-looking значения, дедуплицирует и проставляет `turn_index`. Legacy `discovered_*` поля временно остаются для stage/report compatibility.

## Persistent history и аналитика

Redis хранит активное runtime-состояние. PostgreSQL хранит durable history.

Основные таблицы:

- `training_sessions`
- `training_turns`
- `training_reports`
- `usage_events`
- identity/access/admin tables

Client-facing history:

- `GET /api/history/sessions`
- `GET /api/history/sessions/{session_id}`
- `GET /api/history/sessions/{session_id}/report`

Client/team analytics:

- `GET /api/client/analytics/me`
- `GET /api/team/users`
- `GET /api/team/usage-summary`
- `GET /api/team/users/{user_id}/history/sessions`
- `GET /api/team/users/{user_id}/analytics`

История и аналитика возвращают только public-safe DTO. Saved judge payloads используются для безопасных агрегатов: strongest/weakest skill, judged-session count, 7-day trends, average final interest, completion rate и manager ranking.

## LLM runtime

Runtime разделён на несколько контрактов:

- Persona Generator LLM возвращает `PersonaGenerationOutput`.
- Dialogue Simulator LLM возвращает `LLMTurnResponse`.
- Judge LLM возвращает post-finish judge payload.

Все provider outputs считаются недоверенными и валидируются Pydantic-моделями. Fake/local fallback предназначен для разработки и демо. Staging/prod должны явно конфигурировать реальные credentials и fallback-политику.

Durable history хранит internal metadata версий контрактов:

- persona schema/prompt version;
- dialogue schema/prompt version;
- judge schema/prompt version.

Обычные client-facing DTO не раскрывают raw prompts или provider payloads.

## STT / голосовой ввод

STT — pre-send UX layer:

1. Browser записывает audio через `MediaRecorder`.
2. Frontend отправляет multipart `POST /api/speech/transcribe`.
3. Backend проверяет auth, CSRF, optional session ownership, размер, content type, длительность, concurrency и rate limits.
4. Audio конвертируется в WAV 16k mono.
5. STT backend возвращает текст.
6. Нормализованный `text` вставляется в composer.

STT endpoint не создаёт turn, не пишет training history и не отправляет текст в dialogue LLM автоматически.

## CLI

Локальный CLI:

```bash
python -m app.cli.main
```

Команды:

- `/start`
- `/resume`
- `/scenarios`
- `/state`
- `/history`
- `/finish`
- `/help`
- `/exit`

CLI полезен для локальной проверки runtime loop. Authenticated SaaS/history flow живёт в API и frontend; CLI может оставаться runtime-only.

## Admin CLI

Перед использованием примените migrations и проверьте `DATABASE_URL`.

Создать первого внутреннего администратора:

```bash
python -m app.admin.cli create-internal-admin ^
  --client-name "Platform" ^
  --client-slug platform ^
  --email admin@example.com ^
  --password TempPass123
```

Создать организацию:

```bash
python -m app.admin.cli create-client --name "ООО Ромашка" --slug romashka
```

Создать пользователя:

```bash
python -m app.admin.cli create-user --client romashka --email manager@example.com --password TempPass123
```

Создать минимальный training config:

```bash
python -m app.admin.cli create-config ^
  --client romashka ^
  --name "Базовая тренировка"
```

Сбросить пароль:

```bash
python -m app.admin.cli reset-password --email manager@example.com --password NewTempPass123
```

## Проверки

Backend:

```bash
pytest
python -m compileall app tests
```

Frontend:

```bash
cd frontend
npm test
npm run build
```

Docker/nginx/static serving:

```bash
pytest tests/integration/test_nginx_config.py
pytest tests/integration/test_static_frontend.py
```

Полный `pytest` на Windows может быть долгим из-за тяжёлых integration tests. Для диагностики удобно запускать `tests/unit` и отдельные integration-файлы.

## Ограничения MVP

- Live Yandex smoke test не входит в обычный local test suite.
- Organization-level LLM provider configs не управляют основным MVP runtime.
- Billing/payment не реализован.
- Balance/usage surfaces остаются groundwork, а не платёжной системой.
- CLI не является полным SaaS flow и может не писать durable history.
- Fake/local fallbacks предназначены для разработки и демо, а не для production-поведения без явного решения.

## Рекомендуемый demo flow

1. Заполнить `.env`.
2. Запустить PostgreSQL/Redis.
3. Применить migrations.
4. Создать `internal_admin`.
5. Открыть `/login`, войти админом.
6. Создать организацию.
7. Создать training config с `persona_generation_context`.
8. Создать `client_lead` или `client_manager`.
9. Задать default config пользователю.
10. Войти клиентским пользователем.
11. Открыть `/app/trainer`.
12. Начать тренировку и отправить несколько сообщений.
13. Завершить сессию.
14. Посмотреть `/app/history`, отчёт, `/app/analytics` и `/app/team-analytics`.
