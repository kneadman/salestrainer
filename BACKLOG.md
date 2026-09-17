# Backlog

> Правило: если задача касается проекта и её нет в этого файле — сначала напиши полноценное ТЗ, потом код.
> Формат ТЗ: Problem → Context → Scope → AC → Decomposition → Risks → Files → DoD.

---
## Активные

(пусто)

## Последние закрытые

- **2026-05-26**: Фича — переключение LLM-роутера через `.env`. Добавлен backend `LLM_BACKEND=openai_compatible` поверх любого OpenAI-compatible роутера (`/chat/completions` или `/responses`). Рефакторинг транспорта: `OpenAICompatibleResponsesClient` → `OpenAICompatibleClient` с `api_style` (`responses`/`chat_completions`), `response_format` (`json_schema`/`json_object`/`none`) и парсингом `choices[].message.content`. Новые env-переменные: `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_API_STYLE`, `LLM_RESPONSE_FORMAT`, `LLM_MODEL`, `LLM_DIALOGUE_MODEL`, `LLM_PERSONA_MODEL`, `LLM_JUDGE_MODEL`, `LLM_SUMMARY_MODEL`. Для `openai_compatible` ролевые системные промпты берутся из `app/prompts/*.md` (`load_client_simulator_prompt`, `load_judge_prompt`, `load_persona_generator_prompt`), строгая JSON-схема передаётся через `response_format`. Startup-валидация и fake fallback-политика расширены на новый backend; `yandex_compatible` сохранён без изменений. Тесты: `tests/unit/test_openai_compatible_backend.py` + расширение summary-компрессора. `pytest` green (unit 241, integration 205 passed / 1 skipped).

- **2026-05-26**: Epic — Блог: раздел статей с управлением в админке. Добавлена модель `BlogPost` с Alembic-миграцией, публичные эндпоинты `GET /api/blog/posts` и `GET /api/blog/posts/{slug}`, admin CRUD `GET/POST/PATCH/DELETE /api/internal/blog/posts` с поиском, загрузка обложек `POST /api/internal/blog/upload-image` (лимит 5 МБ, MIME image/*). Frontend: секция `LatestPostsSection` на лендинге, страницы `BlogListPage` (`/blog`) и `BlogPostPage` (`/blog/{slug}`), admin `BlogPostsPage` (`/admin/blog`) с таблицей, inline-формой, debounce-поиском и переключателем публикации. `python -m compileall`, `npm run build`, `pytest` green.



- **2026-05-23**: Фича — отправка заявок из лендинга в Telegram. Добавлен `TelegramClient` (protocol), `HttpxTelegramClient` и `FakeTelegramClient` (`app/infrastructure/telegram_client.py`). Интегрирована отправка в `submit_landing_lead` после `db_session.commit()` с graceful degradation (ошибка не ломает 202). Проверка `is_spam` перед отправкой. Env-переменные `TELEGRAM_BOT_TOKEN` и `TELEGRAM_LEAD_CHAT_ID` в `Settings` и `.env.example`. Unit-тесты на mock transport, интеграционные тесты на взаимодействие с mock клиентом. `python -m compileall` и `pytest` green.

- **2026-05-23**: Фича — ежедневные снапшоты метрик токенизатора и график в админке. Добавлена модель `TokenUsageSnapshot` с Alembic-миграцией, repository/service методы, CLI-команда `snapshot-token-usage`, endpoint `GET /api/internal/organizations/{id}/token-usage-snapshots`. Frontend: компонент `TokenUsageChart` (SVG line chart, 3 серии), переключатель диапазона («Сегодня / Вчера / Последняя неделя / Кастомный»), сумма за период под графиком, `EmptyState` при отсутствии данных. Инфраструктура запуска: `deploy/snapshot_scheduler.py`, `deploy/snapshot-cron.sh`, сервис `snapshot-token-usage` в `docker-compose.yml`. Unit + integration тесты green, frontend билдится (`npm run build`).

- **2026-05-19**: Epic — Внутренний tokenizer для биллинга клиентов. Добавлен `tiktoken` (cl100k_base), `TokenCounterService`, `TokenCountedResult` DTO. Интегрирован подсчёт токенов во все 3 LLM клиента (`YandexCompatibleLLMClient`, `StructuredPersonaGeneratorClient`, `StructuredJudgeClient`). Создана таблица `token_usage_records` с миграцией Alembic. `HistoryService` сохраняет токены для dialogue, persona generation и judge. Backend API `GET /api/internal/organizations/{id}/token-usage` с агрегацией по пользователям (только admin, 403 для остальных). Frontend: `OrganizationUsageTab` отображает токены в K (тысячах) с таблицей по пользователям. Unit + integration тесты green. Frontend билдится (`npm run build`).
