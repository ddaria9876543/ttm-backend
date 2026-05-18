# TTM Backend

REST API для системы управления задачами. Хакатон Транстелематика.

**Стек:** Python, FastAPI, PostgreSQL, SQLAlchemy

---

## Запуск

1. Установи зависимости:
   pip install -r requirements.txt

2. Создай файл `.env` (скопируй из `.env.example`) и впиши пароль от PostgreSQL

3. Запусти сервер:
   uvicorn app.main:app --reload

4. Документация API: http://localhost:8000/docs

---

## Эндпоинты

| Метод | URL | Описание |
|---|---|---|
| GET | /tasks | Список задач (с фильтрами) |
| POST | /tasks | Создать задачу |
| PATCH | /tasks/{id} | Обновить задачу |
| DELETE | /tasks/{id} | Удалить задачу |
| GET | /dashboard | Аналитика и статистика |
| GET | /users | Список сотрудников |
| GET | /departments | Список отделов |

## Фильтры для /tasks

?status=overdue
?period=week
?priority=high
?department_id=1
?assignee_id=2
?search=текст
