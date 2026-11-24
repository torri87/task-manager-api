# Task Manager API

# Встановлення та запуск

## 1. Клонування репозиторію

```bash
git clone https://github.com/torri87/task-manager-api.git
```

## 2. Налаштування змінних середовища

Переіменуй файл .env.example на .env

Приклад налаштувань для Docker Compose:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=tasks
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tasks

#CHANGE IT
SECRET_KEY=4aeae6b99314622da4b7921a1e716b9639c1f7abf32ce54ba2a986c38e16e065
```

## 3. Збірка та запуск контейнерів

```bash
docker compose up --build -d
```

## 4. Перевірка стану та здоров'я сервісів


Перевірити доступність API та підключення до БД:

- **Health check API:** `http://localhost:8000/`
- **Health check БД:** `http://localhost:8000/health/db`
- **Swagger UI:** `http://localhost:8000/docs`

---


# API Documentation

Базова адреса API:

```text
http://localhost:8000
```

Усі ендпоінти (окрім `/auth/register`, `/auth/login` та health-перевірок) вимагають заголовок авторизації:

```http
Authorization: Bearer <access_token>
```

---

## 1. Автентифікація (`/auth`)

| HTTP-метод | Endpoint | Опис | Доступ |
|---|---|---|---|
| POST | `/auth/register` | Реєстрація нового користувача | Усі |
| POST | `/auth/login` | Вхід та отримання JWT access-токена (`form-data`: `username` = email, `password`) | Усі |
| GET | `/auth/me` | Отримати дані поточного авторизованого користувача | Авторизований користувач |

### Реєстрація

```http
POST /auth/register
Content-Type: application/json
```

```json
{
  "email": "user@example.com",
  "password": "pas123456"
}
```

Відповідь (`201 Created`):

```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-11-24T12:00:00Z"
}
```

### Вхід

Приймає дані у форматі `application/x-www-form-urlencoded`, де поле `username` містить `email` користувача:

```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=user@example.com&password=pas123456
```

Відповідь (`200 OK`):

```json
{
  "access_token": "<jwt_token>",
  "token_type": "bearer"
}
```

### Поточний користувач

```http
GET /auth/me
Authorization: Bearer <access_token>
```

Відповідь (`200 OK`):

```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-11-24T12:00:00Z"
}
```

---

## 2. Задачі (`/tasks`)

| HTTP-метод | Endpoint | Опис | Доступ |
|---|---|---|---|
| POST | `/tasks` | Створити задачу | Авторизований користувач |
| GET | `/tasks` | Список задач з фільтрацією, пошуком, сортуванням та пагінацією | Авторизований користувач |
| GET | `/tasks/overdue` | Список прострочених незавершених задач | Авторизований користувач |
| GET | `/tasks/stats` | Агрегована статистика за статусами, пріоритетами та простроченими задачами | Авторизований користувач |
| GET | `/tasks/{task_id}` | Отримати задачу за ID | Авторизований користувач |
| PATCH | `/tasks/{task_id}` | Оновити поля задачі | Авторизований користувач |
| DELETE | `/tasks/{task_id}` | Видалити задачу (якщо не `In Progress` і не `Review`) | Авторизований користувач |
| PATCH | `/tasks/{task_id}/status` | Змінити статус задачі з перевіркою правил переходів | Авторизований користувач |

### Створення задачі

```http
POST /tasks
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "title": "test1",
  "description": "test desc",
  "priority": "High",
  "assignee_id": 1,
  "deadline": "2026-12-01T18:00:00Z"
}
```

Відповідь (`201 Created`):

```json
{
  "id": 1,
  "title": "test1",
  "description": "test desc",
  "status": "Backlog",
  "priority": "High",
  "assignee_id": 1,
  "author_id": 1,
  "deadline": "2026-12-01T18:00:00Z",
  "created_at": "2026-11-24T12:05:00Z",
  "updated_at": "2026-11-24T12:05:00Z"
}
```

### Пошук, фільтрація, сортування та пагінація (`GET /tasks`)

Приклад:

```http
GET /tasks?search=te&priority=High&sort_by=deadline&order=asc&limit=10&offset=0
Authorization: Bearer <access_token>
```

Відповідь (`200 OK`):

```json
{
  "items": [
    {
      "id": 1,
      "title": "test",
      "description": "test desc",
      "status": "Backlog",
      "priority": "High",
      "assignee_id": 1,
      "author_id": 1,
      "deadline": "2026-12-01T18:00:00Z",
      "created_at": "2026-11-24T12:05:00Z",
      "updated_at": "2026-11-24T12:05:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### Зміна статусу задачі

```http
PATCH /tasks/1/status
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "status": "In Progress"
}
```

### Статистика задач (`GET /tasks/stats`)

```http
GET /tasks/stats
Authorization: Bearer <access_token>
```

Приклад відповіді (`200 OK`):

```json
{
  "total": 5,
  "by_status": {
    "Backlog": 2,
    "In Progress": 1,
    "Review": 1,
    "Done": 1,
    "Cancelled": 0
  },
  "by_priority": {
    "Low": 1,
    "Medium": 2,
    "High": 2
  },
  "overdue": 0,
  "active": 4
}
```

---

## 3. Коментарі (`/tasks/{task_id}/comments`)

| HTTP-метод | Endpoint | Опис | Доступ |
|---|---|---|---|
| POST | `/tasks/{task_id}/comments/` | Додати коментар до задачі | Авторизований користувач |
| GET | `/tasks/{task_id}/comments/` | Отримати список коментарів до задачі (`limit`, `offset`) | Авторизований користувач |

### Створення коментаря

```http
POST /tasks/1/comments/
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "content": "Почав роботу над цим завданням."
}
```

Відповідь (`201 Created`):

```json
{
  "id": 1,
  "task_id": 1,
  "author_id": 1,
  "content": "Почав роботу над цим завданням.",
  "created_at": "2026-11-24T12:10:00Z"
}
```

---

# Тестування

Для запуску тестів усередині контейнера `api`:

```bash
docker compose exec api pytest -v
```
