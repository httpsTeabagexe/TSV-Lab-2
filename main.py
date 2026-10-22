# Задание на ЛР2:
# 1. Написать на FastAPI бэкенд с эндпоинтами:
# 1.1. POST, GET, DELETE - для работы с JSON. Структура JSON выбирается вами
# 1.2. Реализовать в Swagger тестирование эндпоинтов
# 1.3. При помощи Pydantic реализовать валидацию данных
# 1.4. Хранение данных - локальное
# 1.5. Упаковать приложение в Docker
#

# os — работа с переменными окружения (например, TSV_DB_PATH)
import os

# sqlite3 — встроенный драйвер для работы с базой данных SQLite
import sqlite3

# asynccontextmanager — декоратор для создания lifespan-контекста FastAPI
from contextlib import asynccontextmanager

# Path — удобная работа с путями файловой системы
from pathlib import Path

# FastAPI — веб-фреймворк для создания API
from fastapi import FastAPI, HTTPException, Path as PathParam, Response, status

# HTMLResponse — возврат HTML-страницы с главного маршрута
from fastapi.responses import HTMLResponse

# Pydantic — валидация и сериализация данных
from pydantic import BaseModel, ConfigDict, Field, field_validator

# путь к файлу sqlite базы
# если запускаем в докере, берем путь из переменной окружения, иначе сохраняем в папку data
DB_PATH = Path(
    os.environ.get("TSV_DB_PATH", Path(__file__).parent / "data" / "tasks.db")
)



# pydantic схемы для валидации входных и выходных данных
class TaskCreate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",                 #запрещает любые левые поля в json, если пришлют - вернется 422
        json_schema_extra={             # пример задачи в схеме OpenAPI
            "examples": [
                {
                    "title": "Подготовить ЛР2",
                    "description": "Проверить запросы к API",
                    "priority": 3,
                    "completed": False,
                }
            ]
        },
    )

    # ... обязательное поле и у него нет дефолта
    title: str = Field(..., max_length=100, description="название задачи (1-100 символов)")
    description: str = Field(default="", max_length=500, description="описание задачи")
    # strict=True чтобы pydantic не приводил строку "3" к числу 3, а требовал строго int
    priority: int = Field(default=3, ge=1, le=5, strict=True, description="приоритет от 1 до 5")
    completed: bool = Field(default=False, strict=True, description="выполнено или нет")

    # валидатор для title обрезаем пробелы и проверяем чтобы строка не была пустой
    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("название не может быть пустым или состоять из одних пробелов")
        return trimmed


# модель задачи для ответа клиенту (наследует TaskCreate и добавляет id)
class Task(TaskCreate):
    # здесь тоже ... означает что id обязательно должен быть
    id: int = Field(..., description="id задачи из базы")

    # очищаем json_schema_extra от родителя чтобы схема ответа выглядела стандартно
    model_config = ConfigDict(json_schema_extra={})


# схема для возврата ошибки 404
class ErrorResponse(BaseModel):
    detail: str = Field(..., description="текст ошибки")


# подключение к sqlite
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    # позволяет обращаться к полям по имени row["title"] а не по индексу row[1]
    conn.row_factory = sqlite3.Row
    return conn


# преобразуем строку из бд в pydantic объект
def row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        priority=row["priority"],
        # sqlite не имеет типа boolean и хранит 0 или 1, поэтому приводим к bool
        completed=bool(row["completed"]),
    )


# lifespan выполняется при старте и завершении приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    # создаем папку data если ее еще нет
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db_connection()
    try:
        # создаем таблицу если еще не создана
        # в sqlite check следит за допустимыми значениями
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER NOT NULL CHECK (priority BETWEEN 1 AND 5),
                completed INTEGER NOT NULL CHECK (completed IN (0, 1))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    yield


# теги для группировки операций в OpenAPI
tags_metadata = [
    {
        "name": "Задачи",
        "description": "основные операции со списком задач",
    }
]

app = FastAPI(
    title="ТСВ ЛР2",
    description="бэк FastAPI с бд SQLite",
    # version="1.0.0",
    lifespan=lifespan,
    openapi_tags=tags_metadata,
    docs_url=None,
)

NOT_FOUND_RESPONSE = {
    404: {"model": ErrorResponse, "description": "задача не найдена"}
}


# простая html страница на главной для удобства проверки
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ТСВ ЛР2</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background-color: #f4f6f8;
            color: #2c3e50;
            padding: 30px 20px;
        }
        .container { max-width: 760px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 2px solid #e2e8f0;
        }
        h1 { font-size: 22px; color: #1a202c; }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            border: 1px solid #e2e8f0;
        }
        .card h2 { font-size: 17px; margin-bottom: 14px; color: #2d3748; }
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #4a5568; }
        input[type="text"], select, textarea {
            width: 100%;
            padding: 9px 12px;
            border: 1px solid #cbd5e0;
            border-radius: 6px;
            font-size: 14px;
            outline: none;
        }
        textarea { resize: vertical; height: 60px; }
        button.btn-submit {
            background-color: #319795;
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
        }
        .error-box {
            display: none;
            background-color: #fff5f5;
            color: #c53030;
            border: 1px solid #feb2b2;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 13px;
            margin-bottom: 12px;
        }
        .task-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 14px;
            border: 1px solid #edf2f7;
            border-radius: 6px;
            margin-bottom: 8px;
            background-color: #ffffff;
        }
        .task-title { font-size: 15px; font-weight: 600; color: #2d3748; margin-bottom: 2px; }
        .task-desc { font-size: 13px; color: #718096; margin-bottom: 4px; }
        .badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 7px;
            border-radius: 4px;
            background-color: #edf2f7;
            color: #4a5568;
        }
        .badge-priority-5 { background-color: #fed7d7; color: #9b2c2c; }
        .badge-priority-4 { background-color: #feebc8; color: #9c4221; }
        .badge-priority-3 { background-color: #e2e8f0; color: #4a5568; }
        .badge-priority-2 { background-color: #e6fffa; color: #234e52; }
        .badge-priority-1 { background-color: #ebf8ff; color: #2b6cb0; }
        .btn-delete {
            background: none;
            border: 1px solid #e53e3e;
            color: #e53e3e;
            padding: 6px 12px;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
        }
        .btn-delete:hover { background-color: #e53e3e; color: white; }
        .empty-tasks { text-align: center; padding: 28px; color: #a0aec0; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Менеджер задач</h1>
                <p style="font-size: 13px; color: #718096; margin-top: 3px;">fastapi + sqlite + pydantic</p>
            </div>
        </header>

        <div class="card">
            <h2>Добавить задачу</h2>
            <div id="errorBox" class="error-box"></div>
            <form id="createForm" onsubmit="handleCreateTask(event)">
                <div class="form-group">
                    <label for="title">Название задачи *</label>
                    <input type="text" id="title" placeholder="например: подготовить отчет" required>
                </div>
                <div class="form-group">
                    <label for="description">Описание</label>
                    <textarea id="description" placeholder="подробности задачи..."></textarea>
                </div>
                <div class="form-group">
                    <label for="priority">Приоритет (1-5)</label>
                    <select id="priority">
                        <option value="1">1 очень низкий</option>
                        <option value="2">2 низкий</option>
                        <option value="3" selected>3 обычный</option>
                        <option value="4">4 высокий</option>
                        <option value="5">5 критический</option>
                    </select>
                </div>
                <button type="submit" class="btn-submit">Создать задачу</button>
            </form>
        </div>

        <div class="card">
            <h2>Список задач</h2>
            <div id="taskList">
                <div class="empty-tasks">Загрузка задач</div>
            </div>
        </div>
    </div>

    <script>
        // подгружаем задачи с сервера
        async function fetchTasks() {
            try {
                const response = await fetch('/tasks');
                if (!response.ok) throw new Error('ошибка загрузки');
                const tasks = await response.json();

                const container = document.getElementById('taskList');
                if (tasks.length === 0) {
                    container.innerHTML = '<div class="empty-tasks">Задач пока нет. Добавьте задачу выше.</div>';
                    return;
                }

                container.innerHTML = tasks.map(task => `
                    <div class="task-item">
                        <div>
                            <div class="task-title">
                                #${task.id} ${escapeHtml(task.title)}
                                <span class="badge badge-priority-${task.priority}">Приоритет: ${task.priority}</span>
                            </div>
                            ${task.description ? `<div class="task-desc">${escapeHtml(task.description)}</div>` : ''}
                        </div>
                        <button class="btn-delete" onclick="handleDeleteTask(${task.id})">Удалить</button>
                    </div>
                `).join('');
            } catch (err) {
                document.getElementById('taskList').innerHTML = '<div class="empty-tasks" style="color: red;">Ошибка загрузки задач</div>';
            }
        }

        // отправка новой задачи
        async function handleCreateTask(event) {
            event.preventDefault();
            const errorBox = document.getElementById('errorBox');
            errorBox.style.display = 'none';

            const payload = {
                title: document.getElementById('title').value,
                description: document.getElementById('description').value,
                priority: parseInt(document.getElementById('priority').value, 10),
                completed: false
            };

            try {
                const response = await fetch('/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (response.status === 201) {
                    document.getElementById('title').value = '';
                    document.getElementById('description').value = '';
                    document.getElementById('priority').value = '3';
                    fetchTasks();
                } else {
                    const errData = await response.json();
                    errorBox.textContent = 'Ошибка: ' + JSON.stringify(errData.detail || errData);
                    errorBox.style.display = 'block';
                }
            } catch (err) {
                errorBox.textContent = 'Ошибка соединения с сервером';
                errorBox.style.display = 'block';
            }
        }

        // удаление задачи
        async function handleDeleteTask(taskId) {
            if (!confirm(`Удалить задачу #${taskId}?`)) return;

            try {
                const response = await fetch(`/tasks/${taskId}`, { method: 'DELETE' });
                if (response.status === 204) {
                    fetchTasks();
                } else {
                    alert('Не удалось удалить задачу');
                    fetchTasks();
                }
            } catch (err) {
                alert('Ошибка сети при удалении');
            }
        }

        // простая защита от xss
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        fetchTasks();
    </script>
</body>
</html>
"""


# главная страница не входит в схему OpenAPI
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    return HTMLResponse(content=HTML_TEMPLATE)


@app.post(
    "/tasks",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    tags=["Задачи"],
    summary="Создать задачу",
)
def create_task(data: TaskCreate, response: Response) -> Task:
    conn = get_db_connection()
    try:
        # VALUES (?, ?, ?, ?) это параметризованный sql запрос тобишь плейсхолдеры вместо f строк
        # библиотека sqlite3 сама экранирует данные и подставляет их на место знаков вопроса
        # нужно защиты от sql инъекций
        cursor = conn.execute(
            """
            INSERT INTO tasks (title, description, priority, completed)
            VALUES (?, ?, ?, ?)
            """,
            (data.title, data.description, data.priority, int(data.completed)),
        )
        # фиксируем изменения в базе данных, иначе транзакция отменится
        conn.commit()
        # lastrowid специальное свойство курсора sqlite, которое возвращает id только что вставленной строки
        task_id = cursor.lastrowid
    finally:
        conn.close()

    # model dump ереводит pydantic объект в обычный python словарь
    # две звездочки ** распаковывают словарь в именованные аргументы конструктора Task(id=..., title=..., ...)
    task = Task(id=task_id, **data.model_dump())

    response.headers["Location"] = f"/tasks/{task.id}"
    return task


@app.get(
    "/tasks",
    response_model=list[Task],
    tags=["Задачи"],
    summary="Получить список задач",
)
def list_tasks() -> list[Task]:
    conn = get_db_connection()
    try:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id ASC").fetchall()
    finally:
        conn.close()

    # собираем список моделей Task через списковое включение
    return [row_to_task(row) for row in rows]


@app.get(
    "/tasks/{task_id}",
    response_model=Task,
    responses=NOT_FOUND_RESPONSE,
    tags=["Задачи"],
    summary="Получить задачу по ID",
)
def get_task(
    # ... обязательный параметр пути
    # ge=1 greater or equal id >= 1
    task_id: int = PathParam(..., ge=1, description="id задачи")
) -> Task:
    conn = get_db_connection()
    try:
        # здесь тоже знак вопроса ? для безопасной подстановки task_id
        # кортеж из одного элемента пишется с запятой (task_id,), иначе скобки не создадут кортеж
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    return row_to_task(row)


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_RESPONSE,
    tags=["Задачи"],
    summary="Удалить задачу по ID",
)
def delete_task(
    task_id: int = PathParam(..., ge=1, description="id задачи для удаления")
) -> Response:
    conn = get_db_connection()
    try:
        result = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
    finally:
        conn.close()

    # result.rowcount показывает сколько строк было затронуто sql запросом
    # если rowcount == 0 то значит записи с таким id в таблице не было
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # для статуса 204 No Content возвращаем пустой Response
    return Response(status_code=status.HTTP_204_NO_CONTENT)
