# План рефакторинга Инфо Арены

Документ фиксирует состояние проекта после первого безопасного этапа
рефакторинга. Изменения не меняют публичный API и позволяют выполнять
миграцию постепенно.

## Аудит перегруженных файлов

### Backend

| Файл | Лишние зоны ответственности | Новый слой |
| --- | --- | --- |
| `backend/app/services.py` | сериализация, уведомления, файлы, прогресс и награды, приглашения, мероприятия и дуэли | `services/{serializers,notifications,files,progress,access,events,duels}.py` |
| `backend/app/schemas.py` | DTO авторизации, организации, обучения, социальных функций и уведомлений в одном модуле | `schemas/{auth,organization,learning,social,notifications}.py` |
| `backend/app/routes/learning.py` | HTTP, загрузка файлов, homework/event use-cases и SQL-запросы | следующий этап: `routes/learning/*`, `services/homework.py`, `services/events.py`, `repositories/{homework,events}.py` |
| `backend/app/routes/manage.py` | HTTP, права доступа, CRUD учреждения и управление наградами | следующий этап: `services/organization.py`, `services/rewards.py`, domain repositories |
| `backend/app/routes/social.py` | HTTP, поиск пользователей, дружба, дуэли и расчёт scoreboard | следующий этап: `services/friendships.py`, `services/duels.py`, `repositories/social.py` |
| `backend/app/main.py` | создание приложения, seed, scheduler, static files и health endpoint | `app/factory.py`, `app/lifecycle.py`, `routes/health.py` |

`models.py` не следует дробить механически: это единый SQLAlchemy metadata
слой. Если число моделей продолжит расти, его стоит разделить по доменам с
единым `models/base.py` и импортом всех моделей в `models/__init__.py` для
Alembic.

### Frontend

| Файл | Лишние зоны ответственности | Рекомендация |
| --- | --- | --- |
| `frontend/src/layout.css` | management, social, navigation, responsive и dark-theme правила | уже разделён на `src/styles/*.css` |
| `frontend/src/style.css` | design tokens, primitives и page layouts | следующий этап: `styles/tokens.css`, `styles/primitives.css`, `styles/pages/*.css` |
| `frontend/src/App.vue` | shell, auth states, header, navigation, toast logic и MAX bridge | `components/layout/{AppHeader,BottomNav,ToastStack}.vue`, `composables/useMaxBackButton.js` |
| `frontend/src/stores/arena.js` | auth session, WebSocket, notifications, student data, toasts и mutation lock | `stores/session.js`, `stores/notifications.js`, `stores/learning.js`, `services/ws.js` |
| `frontend/src/pages/Manager.vue` (981 строка) | пять management-разделов, модальные формы и CRUD | `pages/manager/*.vue`, `components/manager/*.vue`, `services/management.js` |
| `frontend/src/pages/Teacher.vue` (641 строка) | homework, review, events и participants | `pages/teacher/{Homework,Events}.vue` |

## Новая структура

```text
backend/
├── app/
│   ├── main.py                 # composition root
│   ├── routes/                 # HTTP/WebSocket adapters
│   ├── services/               # use-cases by domain
│   │   ├── access.py
│   │   ├── duels.py
│   │   ├── events.py
│   │   ├── files.py
│   │   ├── notifications.py
│   │   ├── progress.py
│   │   └── serializers.py
│   ├── repositories/            # reusable data-access queries
│   │   ├── notifications.py
│   │   └── users.py
│   ├── schemas/                 # request DTOs and validation
│   ├── models.py                # SQLAlchemy entities
│   └── db.py                    # session/transaction boundary
├── migrations/
├── tests/
├── pyproject.toml
└── uv.lock

frontend/src/
├── components/                 # reusable UI primitives
├── pages/                     # route-level compositions
├── services/
│   └── http.js                 # transport boundary
├── stores/                     # Pinia state
├── styles/
│   ├── management.css
│   ├── navigation.css
│   ├── responsive.css
│   ├── social.css
│   ├── theme.css
│   └── misc.css
├── api.js                      # compatibility facade
└── App.vue
```

## Миграция на uv

`backend/pyproject.toml` теперь содержит runtime dependencies и отдельную
`dev` dependency group. `backend/uv.lock` является единственным lock-файлом
Python-зависимостей. Старый `requirements.txt` удалён.

```bash
# установка runtime + dev dependencies
uv sync --directory backend

# миграции и API
uv run --directory backend alembic upgrade head
uv run --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000

# тесты и линтер
PYTHONPATH=backend uv run --directory backend pytest -q
uv run --directory backend ruff check .

# MAX bot
uv run --directory backend python -m app.bot
```

Docker использует официальный образ `uv`, `uv sync --frozen --no-dev` и
кэш `/root/.cache/uv`; `pip install -r requirements.txt` больше не нужен.

## Следующие этапы

1. Вынести use-case классы `HomeworkService`, `EventService`,
   `OrganizationService` и `FriendshipService`; роуты должны только разобрать
   запрос, вызвать use-case и вернуть DTO.
2. Перенести SQL из роутов в repositories и добавить response DTO вместо
   универсального `row()`.
3. Разделить `Manager.vue`, `Teacher.vue`, `App.vue` и `arena.js` по границам
   ответственности, не меняя URL и Pinia public contract за один релиз.
4. Добавить TypeScript после стабилизации границ: `vue-tsc`, типы API и
   автоматическую генерацию OpenAPI client. Не стоит одновременно менять Vue
   на React/Nuxt: текущая связка Vue 3 + Vite + Pinia хорошо подходит SPA.
5. Для UI можно добавить `@vueuse/core` (composables), `vee-validate` +
   `zod` (сложные формы) и `unplugin-vue-components` (автоимпорт). Tailwind
   уже подключён, но смешивание utility-классов с глобальным CSS следует
   постепенно сокращать, а не переписывать весь интерфейс сразу.
