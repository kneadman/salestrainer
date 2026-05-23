# Backlog

> Правило: если задача касается проекта и её нет в этого файле — сначала напиши полноценное ТЗ, потом код.
> Формат ТЗ: Problem → Context → Scope → AC → Decomposition → Risks → Files → DoD.

---

## Последние закрытые

- **2026-05-23**: Фича — отправка заявок из лендинга в Telegram. Добавлен `TelegramClient` (protocol), `HttpxTelegramClient` и `FakeTelegramClient` (`app/infrastructure/telegram_client.py`). Интегрирована отправка в `submit_landing_lead` после `db_session.commit()` с graceful degradation (ошибка не ломает 202). Проверка `is_spam` перед отправкой. Env-переменные `TELEGRAM_BOT_TOKEN` и `TELEGRAM_LEAD_CHAT_ID` в `Settings` и `.env.example`. Unit-тесты на mock transport, интеграционные тесты на взаимодействие с mock клиентом. `python -m compileall` и `pytest` green.

- **2026-05-23**: Фича — ежедневные снапшоты метрик токенизатора и график в админке. Добавлена модель `TokenUsageSnapshot` с Alembic-миграцией, repository/service методы, CLI-команда `snapshot-token-usage`, endpoint `GET /api/internal/organizations/{id}/token-usage-snapshots`. Frontend: компонент `TokenUsageChart` (SVG line chart, 3 серии), переключатель диапазона («Сегодня / Вчера / Последняя неделя / Кастомный»), сумма за период под графиком, `EmptyState` при отсутствии данных. Инфраструктура запуска: `deploy/snapshot_scheduler.py`, `deploy/snapshot-cron.sh`, сервис `snapshot-token-usage` в `docker-compose.yml`. Unit + integration тесты green, frontend билдится (`npm run build`).

- **2026-05-19**: Epic — Внутренний tokenizer для биллинга клиентов. Добавлен `tiktoken` (cl100k_base), `TokenCounterService`, `TokenCountedResult` DTO. Интегрирован подсчёт токенов во все 3 LLM клиента (`YandexCompatibleLLMClient`, `StructuredPersonaGeneratorClient`, `StructuredJudgeClient`). Создана таблица `token_usage_records` с миграцией Alembic. `HistoryService` сохраняет токены для dialogue, persona generation и judge. Backend API `GET /api/internal/organizations/{id}/token-usage` с агрегацией по пользователям (только admin, 403 для остальных). Frontend: `OrganizationUsageTab` отображает токены в K (тысячах) с таблицей по пользователям. Unit + integration тесты green. Frontend билдится (`npm run build`).
