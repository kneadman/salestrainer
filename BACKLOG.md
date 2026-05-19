# BACKLOG.md — Sales Trainer

> Рабочий локальный бэклог. Держим коротким: только актуальные задачи и последние закрытые блоки. Секреты, raw LLM payloads и agent notes сюда не добавлять.
>
> **Правило**: любая новая задача по проекту сначала проверяется здесь. Если её нет — декомпозировать (problem / what to do / acceptance criteria / files / suggested PR) и записать в «Актуальный бэклог» до начала работы.

## Актуальный бэклог

*(пусто)*

## Последние закрытые

- 2026-05-19: Epic — Внутренний tokenizer для биллинга клиентов. Добавлен `tiktoken` (cl100k_base), `TokenCounterService`, `TokenCountedResult` DTO. Интегрирован подсчёт токенов во все 3 LLM клиента (`YandexCompatibleLLMClient`, `StructuredPersonaGeneratorClient`, `StructuredJudgeClient`). Создана таблица `token_usage_records` с миграцией Alembic. `HistoryService` сохраняет токены для dialogue, persona generation и judge. Backend API `GET /api/internal/organizations/{id}/token-usage` с агрегацией по пользователям (только admin, 403 для остальных). Frontend: `OrganizationUsageTab` отображает токены в K (тысячах) с таблицей по пользователям. Unit + integration тесты green. Frontend билдится (`npm run build`).

**Problem**: Администратор платформы не видит реального расхода токенов LLM по организациям и пользователям. Сейчас в `usage_events` хранятся только счётчики событий (сессии, ходы), но нет данных о токенах. Это не позволяет прогнозировать стоимость, выставлять счета клиентам и выявлять аномалии потребления.

**Context & Constraints**:
- `usage_events` таблица с JSON `event_payload` уже существует (`app/history/models.py`) — расширяем `event_payload` или создаём отдельную таблицу `token_usage_records`
- LLM вызовы идут через `YandexCompatibleLLMClient.generate_client_turn()`, `StructuredPersonaGeneratorClient.generate_persona()`, `JudgeClient.judge_session()`
- `HistoryService` уже пишет usage events (`record_turn_processed`, `record_session_started`, `record_session_finished`, `record_report_generated`) — идеальное место для прикрепления токенов
- Админка уже имеет `OrganizationUsageTab` и `GET /api/internal/organizations/{id}/usage-summary`
- Токенизация выполняется на стороне приложения (internal tokenizer), без опоры на провайдера

**Scope Boundaries**:
- **IN scope**:
  - Внутренний tokenizer сервис (tiktoken cl100k_base) для подсчёта input/output токенов
  - Интеграция подсчёта во все 3 LLM клиента (dialogue, persona generation, judge)
  - Хранение токенов в БД (новая таблица `token_usage_records` или расширение `usage_events`)
  - Backend API: агрегация токенов по пользователю и по организации (только для admin)
  - Frontend: отображение в `OrganizationUsageTab` в тысячах токенов (K tokens)
- **OUT of scope**:
  - Лимиты/квоты/блокировки по превышению
  - Тарификация и цены
  - Экспорт в CSV/PDF
  - Токенизация на уровне отдельного сообщения (только агрегаты по ходу/сессии/пользователю)

**Acceptance Criteria**:
1. После каждого LLM вызова в БД сохраняются `input_tokens` и `output_tokens`
2. Админ endpoint `GET /api/internal/organizations/{id}/token-usage` возвращает:
   - `total_input_tokens`, `total_output_tokens`, `total_tokens` (sum)
   - `per_user` breakdown: `user_id`, `email`, `total_input`, `total_output`, `total`
3. Только пользователи с `role=admin` имеют доступ к endpoint; 403 для остальных
4. `OrganizationUsageTab` отображает:
   - "Всего токенов: X.Y K" (округление до 1 десятичного знака)
   - "Input: X.Y K"
   - "Output: X.Y K"
   - Таблица "По пользователям" с колонками: Пользователь, Input (K), Output (K), Всего (K)
5. Для диалога токены считаются для полного payload (system prompt + persona + history + user message)
6. Для persona generation и judge — для их respective payloads
7. Unit тест на tokenizer сервис: известная строка даёт ожидаемое количество токенов
8. Интеграционный тест: после прохождения хода в БД появляется запись с `token_count > 0`

**Decomposition**:
1. Выбрать и внедрить tokenizer библиотеку (`tiktoken`) в зависимости — S
2. Создать `TokenCounterService` с методами `count_messages()`, `count_string()` — S
3. Расширить LLM клиенты для возврата токенов (обернуть вызовы через DTO) — M
   - `YandexCompatibleLLMClient` (dialogue)
   - `StructuredPersonaGeneratorClient`
   - `JudgeClient`
4. Добавить хранение токенов в БД (миграция: новая таблица `token_usage_records`) — M
5. Обновить `HistoryService` для сохранения токенов вместе с событиями — S
6. Backend API: `GET /api/internal/organizations/{id}/token-usage` с агрегацией SQLAlchemy — M
7. Frontend: обновить `admin/api.ts`, `adminViewModels.ts`, `OrganizationUsageTab` — M
8. Тесты: unit tokenizer + integration token persistence + API authz — M

**Risks & Mitigations**:
- Риск: tiktoken (cl100k_base) приближённо считает токены для YandexGPT. Митигация: использовать как internal estimate, в UI показывать пометку "приближённые токены"
- Риск: подсчёт токенов для больших payload замедляет ответ LLM. Митигация: кэшировать `Encoding` объект сервиса, измерить latency на 95th percentile
- Риск: таблица `token_usage_records` быстро растёт. Митигация: индексы по `(client_account_id, user_id, created_at)`, в будущем — партиционирование или TTL
- Риск: изменение сигнатуры LLM клиентов сломает моки в тестах. Митигация: возвращать NamedTuple/DTO вместо bare tuple

**Affected Files** (предварительно):
- `pyproject.toml` / `uv.lock` — добавить `tiktoken`
- `app/domain/token_counter.py` — новый сервис
- `app/infrastructure/llm_client.py` — интеграция подсчёта
- `app/infrastructure/persona_generator_client.py` — интеграция подсчёта
- `app/infrastructure/judge_client.py` — интеграция подсчёта
- `app/history/models.py` — новая модель `TokenUsageRecord`
- `app/history/service.py` — сохранение токенов
- `app/history/internal_routes.py` — endpoint `token-usage`
- `app/history/schemas.py` — DTOs `TokenUsageSummaryDTO`, `PerUserTokenUsageDTO`
- `frontend/src/admin/api.ts` — `getTokenUsage()`
- `frontend/src/viewModels/adminViewModels.ts` — `buildTokenUsageViewModel()`
- `frontend/src/admin/organizationDetail/OrganizationUsageTab.tsx` — UI
- Alembic миграция

**Definition of Done**:
- Код написан, backend типизация проходит, frontend билдится (`npm run build`)
- Unit + integration тесты на новые пути написаны и проходят
- Ручная проверка: прохождение тренировки → проверка в БД, что `token_usage > 0` → открытие админки → корректные цифры в K
- `BACKLOG.md` обновлён
- Нет секретов, токенов, захардкоженных credentials в коде

**PR Naming & Rollback**:
- Branch: `feature/internal-tokenizer-billing`
- PR title: `feat(billing): add internal tokenizer and org-level token usage metrics`
- Rollback: revert мерж-коммита + откат миграции Alembic

## Последние закрытые

- 2026-05-18: Epic 12 закрыт — Seed-Oriented Persona Generation. Добавлена структурированная seed-конфигурация для генерации персон: 16 блоков (training_context, product, lpr_and_roles, orientation lists, novelty, starting_params). Универсальный prompt-шаблон `app/prompts/persona_seed_template.md` рендерится через Jinja2. Master instruction хранится на стороне LLM (Yandex agent). Backend: `seed_config` JSON колонка в `client_training_configs`, Pydantic модель `PersonaSeedConfig`, `SeedPromptRenderer`, backward compatibility с legacy free-text. Admin API DTOs обновлены. Frontend: toggle seed/legacy, tag-like inputs через `;`, `SeedConfigForm` с fieldset-группировкой, badge Seed/Legacy в таблице. Unit + integration tests green.
- 2026-05-16: Epic 9 закрыт — добавлены frontend regression tests (90 tests), backend contract tests (LLM/judge fallback, persona generation, report read path, public projection boundaries, startup validation), CI smoke guards (`timeout-minutes` для всех jobs, `docker compose config` проверка синтаксиса).
- 2026-05-15: Epic 8.1 закрыт — legacy persona normalization сохранена как compatibility-loader для старых Redis/PostgreSQL session JSON; новые personas остаются universal v3.1 без legacy accounting field names.
- 2026-05-16: Epic 7 закрыт — `OrganizationDetailPage.tsx` разделён на таб-компоненты (`OrganizationUsersTab`, `OrganizationTrainingConfigsTab`, `OrganizationHistoryTab`, `OrganizationUsageTab`, `OrganizationAuditTab`) с shared hook `useOrganizationDetail`; frontend форматтеры вынесены в `frontend/src/viewModels/` (adminViewModels + clientViewModels) — компоненты получают готовые view-models вместо raw backend values.
- 2026-05-15: Epic 8.2 закрыт — fake judge/dialogue user-facing copy очищены от `fake judge`, stub/deterministic wording и legacy persona field names.
