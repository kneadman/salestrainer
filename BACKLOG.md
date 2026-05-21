# Backlog

> Правило: если задача касается проекта и её нет в этого файле — сначала напиши полноценное ТЗ, потом код.
> Формат ТЗ: Problem → Context → Scope → AC → Decomposition → Risks → Files → DoD.

---

### Фича: отправка заявок из лендинга в Telegram

**Problem**: Заявки с демо-формы лендинга (`POST /api/leads`) сохраняются в БД, но команда не получает мгновенного уведомления о новом лиде. Приходится периодически проверять таблицу `landing_leads` вручную или через админку, которой пока нет. Из-за этого ответ на заявку может задерживаться.

**Context & Constraints**:
- Лендинг: `frontend/src/landing/sections/DemoFormSection.tsx` — форма с полями: имя, email, телефон, компания, роль, размер команды, комментарий, согласия.
- Backend endpoint: `POST /api/leads` в `app/api/routes.py` — сохраняет `LandingLead` в БД, применяет rate-limit, проверяет `consent_personal_data === true`, возвращает `202 Accepted`.
- Таблица: `landing_leads` (`app/access/models.py`) уже содержит все нужные поля.
- В проекте **нет** существующей инфраструктуры уведомлений (ни Telegram, ни email, ни webhook).
- В `pyproject.toml` уже есть зависимость `httpx>=0.27,<1.0`.
- Polling бота не требуется — нужен только односторонний push (fire-and-forget) при создании лида.
- Отправка в Telegram **не должна блокировать** HTTP-ответ пользователю и **не должна ломать** приём заявки при сбое доставки.

**Scope Boundaries**:
- **IN scope**:
  - Сервис отправки сообщений в Telegram через Bot API (`sendMessage`) с использованием `httpx`.
  - Интеграция вызова сервиса в `submit_landing_lead` после успешного `db_session.commit()`.
  - Env-переменные: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_LEAD_CHAT_ID`.
  - Формат сообщения: краткая сводка по заявке (имя, контакт, компания, комментарий, UTM).
  - Graceful degradation: ошибка отправки логируется, но пользователю всё равно возвращается `202 Accepted`.
- **OUT of scope**:
  - Polling / webhook / long-polling бота (входящие сообщения, команды).
  - Обратная связь из Telegram в приложение.
  - Очередь задач (Celery, RQ, etc.) — пока простой синхронный или фоновый HTTP-вызов в рамках request lifecycle.
  - HTML-разметка или кнопки в сообщении Telegram.
  - Админка для просмотра заявок.

**Acceptance Criteria**:
1. При валидной заявке через `/api/leads` после сохранения в БД в указанный Telegram-чат приходит сообщение с данными заявки.
2. Формат сообщения читаемый (многострочный текст), содержит: имя, email, телефон, компания, роль, размер команды, комментарий (если есть), UTM-метки (если есть), timestamp.
3. Если `TELEGRAM_BOT_TOKEN` или `TELEGRAM_LEAD_CHAT_ID` не заданы — отправка молча пропускается, логируется на уровне `INFO` или `WARNING`.
4. Если Telegram API возвращает ошибку (невалидный токен, недоступность сети) — заявка в БД всё равно сохранена, пользователю возвращается `202`, ошибка логируется на уровне `ERROR`.
5. Rate-limit на `/api/leads` продолжает работать: ошибка 429 возвращается до создания записи в БД и до попытки отправки в Telegram.
6. В `.env.example` добавлены новые переменные с пустыми значениями и комментариями.
7. В `Settings` (`app/infrastructure/config.py`) добавлены типизированные поля для новых env-переменных.

**Decomposition**:
1. Добавить `telegram_bot_token`, `telegram_lead_chat_id` в `Settings` и `.env.example` — S
2. Создать `app/infrastructure/telegram_client.py`: протокол + реализация на `httpx`, fake-реализация для local/test — M
3. Интегрировать вызов Telegram-клиента в `submit_landing_lead` (`app/api/routes.py`) после `db_session.commit()` — S
4. Написать unit-тесты на `telegram_client` (mock transport) и на хендлер (mock client) — M
5. Ручная проверка: отправить заявку из формы / curl → убедиться что сообщение пришло в чат — S

**Risks & Mitigations**:
- **Риск**: задержка HTTP-запроса к Telegram API замедлит ответ пользователю. **Митигация**: использовать `httpx` с коротким таймаутом (5–7 секунд) и оборачивать вызов в `try/except`; в будущем можно вынести в background task или очередь.
- **Риск**: токен или chat_id попадут в логи. **Митигация**: никогда не логировать `TELEGRAM_BOT_TOKEN`; при ошибке логировать только HTTP status и response body без тела запроса.
- **Риск**: спам-заявки (honeypot) тоже будут отправляться в Telegram. **Митигация**: проверять `is_spam` перед отправкой; спам-заявки не отправлять.

**Affected Files**:
- `app/infrastructure/config.py` — добавить `telegram_bot_token`, `telegram_lead_chat_id`
- `.env.example` — добавить новые переменные
- `app/infrastructure/telegram_client.py` — новый файл: протокол + реализация
- `app/api/routes.py` — вызов telegram-клиента в `submit_landing_lead`
- `tests/unit/infrastructure/test_telegram_client.py` — новый файл (mock transport)
- `tests/integration/test_lead_routes.py` — добавить тест на взаимодействие с mock telegram client

**Definition of Done**:
- Код написан, типизация проходит (`mypy` / `pyright` если применяется)
- Unit/integration тесты написаны и проходят (`pytest`)
- Ручная проверка: заявка через curl → сообщение в Telegram (или в логах при отключённом токене)
- `.env.example` и `BACKLOG.md` обновлены
- Нет захардкоженных токенов / chat_id в коде
- Branch: `feature/telegram-lead-notifications`

---

### Фича: ежедневные снапшоты метрик токенизатора и график в админке

**Problem**: Администратор не может отслеживать динамику использования токенов во времени. Сейчас во вкладке "Использование" организации видны только текущие агрегированные значения (всего, input, output), но невозможно понять, как менялась нагрузка вчера vs позавчера или на прошлой неделе. Без исторических daily-delta данных сложно отлаживать токенайзер, выявлять пики потребления и планировать лимиты.

**Context & Constraints**:
- В prod-версии уже работает токенайзер (tiktoken-подобный), который считает input/output токены для LLM-запросов и выводит агрегаты во вкладке "Использование" организации в админке.
- В проекте **нет** фонового планировщика задач (Celery, APScheduler, cron).
- Админский фронтенд использует React 18 + TypeScript + Tailwind CSS, кастомные CSS-графики (`AdminBars`), внешние chart-библиотеки отсутствуют.
- Бэкенд: FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL.
- Таймзона для снапшотов — Europe/Moscow (MSK, UTC+3).
- Существующий usage summary endpoint (`GET /api/internal/organizations/{id}/usage-summary`) возвращает агрегаты по сессиям, но не по токенам.

**Scope Boundaries**:
- **IN scope**:
  - SQLAlchemy-модель `TokenUsageSnapshot` для ежедневных снапшотов: `organization_id`, `snapshot_date`, `total_tokens`, `input_tokens`, `output_tokens` (daily delta).
  - Alembic-миграция.
  - Механизм сбора снапшотов — CLI-команда (`python -m app.admin.cli snapshot-token-usage`) для запуска в 00:00 MSK (через cron / docker-compose wrapper / APScheduler — минимально-инвазивный вариант).
  - Backend API `GET /api/internal/organizations/{organization_id}/token-usage-snapshots` с query-параметрами `from_date`, `to_date`.
  - Frontend: линейный график daily delta в `OrganizationUsageTab` с переключателем диапазона.
  - Диапазоны: "Сегодня", "Вчера", "Последняя неделя", "Кастомный" (два input date + кнопка "Применить").
  - Сумма за выбранный период (total / input / output) под графиком.
- **OUT of scope**:
  - Реализация самого токенизатора (уже есть в проде).
  - Агрегация по отдельным пользователям/сценариям в рамках этого ТЗ (только organization-level daily totals).
  - Экспорт в CSV/Excel.
  - Алерты/уведомления при превышении лимитов.
  - Мобильная адаптация графика.

**Acceptance Criteria**:
1. В 00:00 MSK каждый день для каждой организации создаётся ровно один снапшот с daily-delta значениями `total_tokens`, `input_tokens`, `output_tokens` за прошедшие сутки (00:00–23:59 MSK предыдущего дня).
2. Если за сутки токенов не было (нет LLM-вызовов), снапшот создаётся с нулями — не пропускается.
3. API `GET /api/internal/organizations/{id}/token-usage-snapshots?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD` возвращает список снапшотов по возрастанию даты, HTTP 200. Если даты не указаны — последние 30 дней по умолчанию.
4. Во вкладке "Использование" организации под текущим блоком токенов отображается линейный график (CSS/SVG) с тремя сериями: total, input, output.
5. График поддерживает переключение диапазона без перезагрузки страницы:
   - "Сегодня" — показывает снапшот за текущие сутки (если уже создан) или пустое состояние.
   - "Вчера" — снапшот за вчера.
   - "Последняя неделя" — последние 7 полных дней (не включая сегодня, если снапшот ещё не создан).
   - "Кастомный" — два `input type="date"`, кнопка "Применить". Максимальный диапазон — 90 дней.
6. При выборе диапазона под графиком отображается сумма за период: "Всего токенов: X · Input: Y · Output: Z".
7. Если за выбранный период нет снапшотов — отображается `EmptyState` с текстом "Нет данных за выбранный период".
8. Даты в UI отображаются в формате DD.MM.YYYY, timezone Europe/Moscow.
9. Существующий блок "Использование токенов (приближённые)" и остальная вкладка "Использование" продолжают работать без изменений.
10. Запрос к API при смене диапазона занимает <300 мс (сетевой round-trip) при диапазоне до 90 дней.

**Decomposition**:
1. Создать модель `TokenUsageSnapshot` и Alembic-миграцию — S
2. Добавить repository-методы для чтения/записи снапшотов в `app/history/repository.py` — S
3. Добавить service-метод для расчёта daily delta и записи снапшота в `app/history/service.py` — M
4. Добавить CLI-команду `snapshot-token-usage` в `app/admin/cli.py` — S
5. Добавить API endpoint `GET /api/internal/organizations/{id}/token-usage-snapshots` в `app/history/internal_routes.py` — S
6. Добавить тип `TokenUsageSnapshotDTO` в `app/history/schemas.py` — S
7. Обновить `frontend/src/admin/api.ts` — `getTokenUsageSnapshots` — S
8. Обновить `frontend/src/admin/types.ts` — добавить DTO тип — S
9. Создать компонент `TokenUsageChart` (SVG line chart, 3 series) — M
10. Обновить `OrganizationUsageTab` — интегрировать график, переключатель диапазона, сумму за период — M
11. Написать unit-тесты на service/repository + интеграционный тест на endpoint — M
12. Ручная проверка: симулировать снапшоты через CLI → проверить отображение в админке — S

**Risks & Mitigations**:
- **Риск**: токенайзер отсутствует в локальном `main`, интеграция затруднена. **Митигация**: создать протокол `TokenUsageProvider` с методом `get_daily_usage(organization_id, date) -> TokenUsageDelta`; для local/dev предоставить `FakeTokenUsageProvider` (возвращает нули или фиксированные тестовые значения), а реальную реализацию под prod-ветку вынести отдельным PR.
- **Риск**: нет существующего планировщика; добавление APScheduler — новая зависимость в стек. **Митигация**: не внедрять APScheduler в основное приложение. Использовать отдельную CLI-команду и вызывать её через `docker-compose` healthcheck wrapper или системный cron. Это минимально инвазивно.
- **Риск**: дублирование снапшотов при повторном запуске. **Митигация**: unique constraint `(organization_id, snapshot_date)` в БД; при конфликте — `ON CONFLICT DO NOTHING` или перезапись.
- **Риск**: накопление строк в `token_usage_snapshots`. **Митигация**: индекс `(organization_id, snapshot_date)`, композитный primary key по желанию; retention policy (>1 года) — out of scope.
- **Риск**: timezone MSK — переход на летнее/зимнее время. **Митигация**: `zoneinfo.ZoneInfo("Europe/Moscow")` (Python 3.9+), `pytz` не нужен.

**Affected Files**:
- `app/history/models.py` — `TokenUsageSnapshot`
- `migrations/versions/` — alembic revision
- `app/history/repository.py` — CRUD снапшотов
- `app/history/service.py` — агрегация daily delta
- `app/history/schemas.py` — `TokenUsageSnapshotDTO`
- `app/history/internal_routes.py` — endpoint
- `app/admin/cli.py` — CLI-команда
- `frontend/src/admin/api.ts` — `getTokenUsageSnapshots`
- `frontend/src/admin/types.ts` — типы
- `frontend/src/admin/organizationDetail/OrganizationUsageTab.tsx` — интеграция
- `frontend/src/admin/components/TokenUsageChart.tsx` — новый компонент
- `frontend/src/viewModels/adminViewModels.ts` — возможно, viewModel для графика

**Definition of Done**:
- Код написан, типизация проходит (`npm run build`, `pytest`, `python -m compileall`)
- Alembic миграция применяется без ошибок
- Unit/integration тесты на endpoint и сервис написаны и проходят
- Ручная проверка: CLI создаёт снапшоты → админка отображает график за "Последнюю неделю" → сумма под графиком совпадает с ожидаемой
- `BACKLOG.md` обновлён
- Нет захардкоженных credentials или токенов в коде
- Branch: `feature/token-usage-snapshots`

---

## Последние закрытые

- **2026-05-19**: Epic — Внутренний tokenizer для биллинга клиентов. Добавлен `tiktoken` (cl100k_base), `TokenCounterService`, `TokenCountedResult` DTO. Интегрирован подсчёт токенов во все 3 LLM клиента (`YandexCompatibleLLMClient`, `StructuredPersonaGeneratorClient`, `StructuredJudgeClient`). Создана таблица `token_usage_records` с миграцией Alembic. `HistoryService` сохраняет токены для dialogue, persona generation и judge. Backend API `GET /api/internal/organizations/{id}/token-usage` с агрегацией по пользователям (только admin, 403 для остальных). Frontend: `OrganizationUsageTab` отображает токены в K (тысячах) с таблицей по пользователям. Unit + integration тесты green. Frontend билдится (`npm run build`).
