# Backlog

> Правило: если задача касается проекта и её нет в этого файле — сначала напиши полноценное ТЗ, потом код.
> Формат ТЗ: Problem → Context → Scope → AC → Decomposition → Risks → Files → DoD.

---

## Активные

### Epic: Блог — раздел статей с управлением в админке

**Problem**: Проект не имеет раздела для публикации контента (статей, кейсов, обновлений). Это ограничивает SEO, не даёт делиться экспертизой с потенциальными клиентами, а главная страница не демонстрирует актуальность продукта. Менеджер не может быстро добавить статью без разработчика.

**Context & Constraints**:
- Backend: FastAPI + SQLAlchemy 2.0 + PostgreSQL + Alembic. Все модели лежат в `app/<domain>/models.py`, импортируются в `app/infrastructure/db.py`.
- Admin API уже существует в `app/internal_admin/routes.py` с префиксом `/api/internal`, защитой `require_internal_admin_session` и аудит-логом.
- Frontend: React 18 + TypeScript + Vite. Нет UI-библиотек — чистый CSS с классами `admin-*`. Таблицы, формы, модалки — самописные.
- Главная страница `/` — `LandingPage` из секций (`HeroSection`, `ProblemSection` и др.). Нет раздела новостей/статей.
- Загрузка файлов на сервер не реализована. `apiClient.ts` поддерживает `FormData` body (не ставит `Content-Type` вручную).
- `app/web/static.py` раздаёт `/images` из `frontend/dist/images`.

**Scope Boundaries**:
- **IN scope**:
  - Модель `BlogPost` (title, slug, excerpt, content, cover_image_url, author_name, is_published, published_at, created_at, updated_at)
  - Alembic-миграция
  - Публичный API: `GET /api/blog/posts` (список опубликованных), `GET /api/blog/posts/{slug}` (деталька)
  - Admin API: CRUD статей под `/api/internal/blog/posts` + поиск по title/slug/content
  - Загрузка обложки `POST /api/internal/blog/upload-image` (лимит 5 MB, MIME image/*)
  - Секция «Последние статьи» на главной: 3 карточки (заголовок, excerpt, обложка 16:9, ссылка)
  - Раздел `/admin/blog`: таблица с поиском, inline-форма создания/редактирования, переключатель публикации
- **OUT of scope**:
  - WYSIWYG-редактор (используем `<textarea>` для markdown/plain text)
  - Категории, теги, комментарии, подписка
  - SEO-meta поля (description, keywords)
  - CDN / S3 — картинки пишем на диск в `frontend/public/images/blog/`
  - Soft-delete (удаляем hard-delete с подтверждением)

**Acceptance Criteria**:
1. На главной `/` внизу лендинга выводятся 3 последние опубликованные статьи (сортировка по `published_at desc`). Каждая карточка содержит: обложку 16:9 (фиксированный aspect-ratio), заголовок (max 2 строки), excerpt (max 3 строки), кнопку «Читать». Клик — переход на `/blog/{slug}`. Карточки ведут на страницу `/blog` (см. AC 1a).
1a. Страница `/blog` — отдельная страница со списком всех опубликованных статей. Первый запрос загружает 9 статей (сортировка `published_at desc`). Внизу кнопка «Показать ещё» — подгружает следующие 9 штук (cursor-based пагинация через `?cursor=` или offset-based через `?offset=`). Каждая карточка — обложка 16:9, заголовок, excerpt, автор, дата публикации. Клик — переход на `/blog/{slug}`.
2. `GET /api/blog/posts` возвращает только `is_published=true`, сортировка `published_at desc`, поддерживает `?limit=` (default 9, max 50) и `?offset=` (default 0). Поля: `id`, `slug`, `title`, `excerpt`, `cover_image_url`, `author_name`, `published_at`. В ответе присутствует `total` — общее количество опубликованных статей.
3. `GET /api/blog/posts/{slug}` возвращает полную статью (включая `content`). 404 если не найдена или не опубликована.
4. Admin `GET /api/internal/blog/posts` возвращает все статьи (включая черновики), поддерживает `?search=` (поиск по `title`, `slug`, `content` ILIKE). Сортировка `updated_at desc`.
5. Admin `POST /api/internal/blog/posts` — создание статьи. `slug` генерируется автоматически из `title` (transliterate + kebab-case), но можно передать вручную. Валидация уникальности `slug`.
6. Admin `PATCH /api/internal/blog/posts/{id}` — обновление. `published_at` выставляется автоматически при первой публикации (`is_published` false → true).
7. Admin `DELETE /api/internal/blog/posts/{id}` — hard-delete с подтверждением на фронте.
8. Admin `POST /api/internal/blog/upload-image` принимает `multipart/form-data`, поле `image`. Валидация: размер ≤ 5 MB, MIME `image/*`. Файл сохраняется в `frontend/public/images/blog/{uuid}.{ext}`, возвращается относительный URL `/images/blog/{uuid}.{ext}`. Невалидный файл — 422.
9. В админке раздел `/admin/blog` доступен из sidebar. Страница содержит: заголовок «Статьи блога», поле поиска (debounce 300 мс), таблицу с колонками: заголовок, автор, статус (Badge: Опубликована / Черновик), дата обновления, действия (Редактировать / Удалить).
10. Inline-форма создания/редактирования: поля «Заголовок», «Слаг», «Автор», «Краткое описание» (textarea), «Содержание» (textarea), «Обложка» (input type=file + preview текущей обложки), чекбокс «Опубликована». При создании — кнопка «Создать», при редактировании — «Сохранить» + «Отмена».
11. Frontend production build проходит (`npm run build`). Backend компилируется (`python -m compileall`).

**Decomposition**:
1. Модель `BlogPost` + Alembic миграция — S, блокирует всё
2. Backend: Pydantic schemas + service — S
3. Backend: публичные routes (`/api/blog/posts`, `/api/blog/posts/{slug}`) — S
4. Backend: admin routes (CRUD + search) — M
5. Backend: upload-image endpoint + сохранение на диск — M
6. Frontend: компонент `LatestPostsSection` + интеграция в `LandingPage` — M
7. Frontend: страница `BlogListPage` (`/blog`) — список статей + кнопка «Показать ещё» — M
8. Frontend: страница `BlogPostPage` (деталька статьи) — S
9. Frontend: admin `BlogPostsPage` (таблица + поиск + inline-форма) — L
10. Frontend: API-функции в `admin/api.ts` + типы — S
11. Frontend: навигация в `AdminLayout` + роут в `AdminApp` — S
12. Backend: unit + integration тесты — M
13. Ручная проверка: E2E flow — S

**Risks & Mitigations**:
- **Риск**: загрузка больших/вредоносных файлов. **Митигация**: лимит 5 MB, MIME валидация `image/*`, ренейм в UUID + сохранение оригинального расширения, хранение вне `app/`.
- **Риск**: коллизия slug. **Митигация**: unique constraint в БД + валидация в Pydantic schema (query на существование).
- **Риск**: hard-delete статьи ломает ссылки. **Митигация**: фронт показывает модалку подтверждения с текстом «Статья будет удалена безвозвратно». Публичные API отдают только опубликованные, так что 404 ожидаем.
- **Риск**: обложка не 16:9 выглядит плохо. **Митигация**: CSS `aspect-ratio: 16/9` + `object-fit: cover` на фронте. В форме админки подпись «Рекомендуемое соотношение 16:9».
- **Риск**: много файлов-обложек захламляют диск. **Митигация**: out of scope для MVP; при обновлении обложки старый файл не удаляется (можно добавить garbage collector позже).
- **Риск**: offset-based пагинация на больших объёмах работает медленно. **Митигация**: для MVP (до 1000 статей) offset приемлем; при росте контента мигрировать на cursor-based (`published_at` + `id` composite).

**Affected Files** (производные от кодовой базы):
- `app/blog/models.py` — новая модель `BlogPost`
- `app/blog/schemas.py` — DTO `BlogPostDTO`, `BlogPostCreateRequest`, `BlogPostUpdateRequest`
- `app/blog/service.py` — бизнес-логика, DTO-маппинг
- `app/blog/routes.py` — публичные эндпоинты
- `app/blog/admin_routes.py` — admin CRUD + upload
- `app/infrastructure/db.py` — импорт `app.blog.models`
- `app/web/static.py` — возможно, mount для `/images/blog`
- `migrations/versions/` — Alembic миграция
- `frontend/src/components/LandingPage.tsx` — добавить `LatestPostsSection`
- `frontend/src/components/LatestPostsSection.tsx` — новый компонент
- `frontend/src/components/BlogListPage.tsx` — страница списка всех статей
- `frontend/src/components/BlogPostPage.tsx` — страница детальки статьи
- `frontend/src/App.tsx` — роуты `/blog` и `/blog/:slug`
- `frontend/src/admin/AdminApp.tsx` — роут `blog`
- `frontend/src/admin/AdminLayout.tsx` — пункт «Блог» в `NAV_ITEMS`
- `frontend/src/admin/BlogPostsPage.tsx` — новая страница управления
- `frontend/src/admin/api.ts` — функции `listBlogPosts`, `createBlogPost`, `updateBlogPost`, `deleteBlogPost`, `uploadBlogImage`
- `frontend/src/admin/types.ts` — тип `BlogPostDTO`
- `tests/integration/test_blog_routes.py` — новые тесты
- `tests/unit/test_blog_service.py` — новые тесты

**Definition of Done**:
- Код написан, `python -m compileall` проходит без ошибок
- `npm run build` проходит без ошибок TypeScript/Vite
- Alembic миграция применяется (`alembic upgrade head`)
- Unit + integration тесты на новые backend-пути написаны и проходят (`pytest`)
- Ручная проверка: создать статью в админке → загрузить обложку → опубликовать → увидеть на главной → открыть `/blog/{slug}`
- Ручная проверка admin: поиск по названию, редактирование слага, смена статуса, удаление с подтверждением
- `BACKLOG.md` обновлён (этот epic перенесён в «Последние закрытые» или помечен статусом)
- Нет захардкоженных credentials, путей, секретов

**PR Naming & Rollback**:
- Branch: `feature/blog`
- PR title: `feat(blog): add blog section with admin CRUD and landing page integration`
- Rollback: revert мерж-коммита + `alembic downgrade` на одну ревизию

---

## Последние закрытые

- **2026-05-23**: Фича — отправка заявок из лендинга в Telegram. Добавлен `TelegramClient` (protocol), `HttpxTelegramClient` и `FakeTelegramClient` (`app/infrastructure/telegram_client.py`). Интегрирована отправка в `submit_landing_lead` после `db_session.commit()` с graceful degradation (ошибка не ломает 202). Проверка `is_spam` перед отправкой. Env-переменные `TELEGRAM_BOT_TOKEN` и `TELEGRAM_LEAD_CHAT_ID` в `Settings` и `.env.example`. Unit-тесты на mock transport, интеграционные тесты на взаимодействие с mock клиентом. `python -m compileall` и `pytest` green.

- **2026-05-23**: Фича — ежедневные снапшоты метрик токенизатора и график в админке. Добавлена модель `TokenUsageSnapshot` с Alembic-миграцией, repository/service методы, CLI-команда `snapshot-token-usage`, endpoint `GET /api/internal/organizations/{id}/token-usage-snapshots`. Frontend: компонент `TokenUsageChart` (SVG line chart, 3 серии), переключатель диапазона («Сегодня / Вчера / Последняя неделя / Кастомный»), сумма за период под графиком, `EmptyState` при отсутствии данных. Инфраструктура запуска: `deploy/snapshot_scheduler.py`, `deploy/snapshot-cron.sh`, сервис `snapshot-token-usage` в `docker-compose.yml`. Unit + integration тесты green, frontend билдится (`npm run build`).

- **2026-05-19**: Epic — Внутренний tokenizer для биллинга клиентов. Добавлен `tiktoken` (cl100k_base), `TokenCounterService`, `TokenCountedResult` DTO. Интегрирован подсчёт токенов во все 3 LLM клиента (`YandexCompatibleLLMClient`, `StructuredPersonaGeneratorClient`, `StructuredJudgeClient`). Создана таблица `token_usage_records` с миграцией Alembic. `HistoryService` сохраняет токены для dialogue, persona generation и judge. Backend API `GET /api/internal/organizations/{id}/token-usage` с агрегацией по пользователям (только admin, 403 для остальных). Frontend: `OrganizationUsageTab` отображает токены в K (тысячах) с таблицей по пользователям. Unit + integration тесты green. Frontend билдится (`npm run build`).
