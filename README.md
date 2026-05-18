# ТТМ Backend — FastAPI + PostgreSQL

## Структура проекта

```
backend/
├── app/
│   ├── main.py            # Точка входа, CORS, роутеры
│   ├── config.py          # Настройки из .env
│   ├── database.py        # Подключение к PostgreSQL
│   ├── models/
│   │   └── models.py      # SQLAlchemy ORM модели
│   ├── schemas/
│   │   └── schemas.py     # Pydantic схемы (request/response)
│   └── routers/
│       ├── tasks.py       # CRUD задач + комментарии
│       ├── dashboard.py   # Аналитика и дашборды
│       └── users.py       # Пользователи и отделы
├── requirements.txt
└── .env.example
```

## Быстрый старт

### 1. Создай БД (если ещё не сделано)
```bash
createdb ttm_db
psql -d ttm_db -f schema.sql
psql -d ttm_db -f seed.sql
```

### 2. Настрой окружение
```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Отредактируй .env — укажи свой пароль от PostgreSQL
```

### 3. Запусти сервер
```bash
uvicorn app.main:app --reload
```

Сервер запустится на http://localhost:8000

### 4. Документация API (Swagger)
Открой в браузере: **http://localhost:8000/docs**
Там можно сразу тестировать все эндпоинты без Postman.

---

## Эндпоинты

### Задачи `/tasks`
| Метод | URL | Описание |
|---|---|---|
| GET | `/tasks` | Список задач с фильтрами |
| GET | `/tasks/{id}` | Одна задача + дочерние |
| POST | `/tasks` | Создать задачу |
| PATCH | `/tasks/{id}` | Обновить задачу (пишет историю) |
| DELETE | `/tasks/{id}` | Удалить задачу |
| GET | `/tasks/{id}/comments` | Комментарии к задаче |
| POST | `/tasks/{id}/comments` | Добавить комментарий |

### Фильтры GET `/tasks`
```
?department_id=1
?assignee_id=2
?status=overdue
?period=week
?priority=high
?deadline_from=2025-07-01&deadline_to=2025-07-31
?search=хакатон
?skip=0&limit=50
```

### Дашборд `/dashboard`
| Метод | URL | Описание |
|---|---|---|
| GET | `/dashboard` | Вся аналитика одним запросом |

Возвращает: общее кол-во задач, разбивку по статусам, по отделам, просрочки, загрузку сотрудников.

### Пользователи и отделы
| Метод | URL | Описание |
|---|---|---|
| GET | `/users` | Список сотрудников |
| GET | `/users/{id}` | Один сотрудник |
| GET | `/departments` | Список отделов |

---

## Для фронтендера

Базовый URL: `http://localhost:8000`

Пример запроса (JS fetch):
```js
// Получить все просроченные задачи
const res = await fetch('http://localhost:8000/tasks?status=overdue');
const tasks = await res.json();

// Создать задачу
const res = await fetch('http://localhost:8000/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    title: 'Новая задача',
    period: 'week',
    priority: 'high',
    assignee_id: 1,
    department_id: 2,
    deadline: '2025-07-25'
  })
});
```

## Для AI-модуля (подруга)

Данные для анализа берутся через:
- `GET /dashboard` — общая статистика
- `GET /tasks?status=overdue` — просроченные
- `GET /tasks?priority=high` — высокий приоритет
- `GET /tasks?period=week` — задачи на неделю
