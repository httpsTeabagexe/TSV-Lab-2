# ТСВ · Лабораторная работа № 2

Через веб-форму или API можно добавить задачу, посмотреть список и удалить запись. API принимает и возвращает JSON. Pydantic проверяет поля задачи перед записью в SQLite.

Веб-интерфейс доступен на `/`. Swagger UI отключён.

## Запуск в Docker

Запустите приложение из каталога с `compose.yaml`.

```powershell
docker compose up --build -d
```

Откройте [страницу списка задач](http://localhost:8000/). Файл `/app/data/tasks.db` хранится в именованном томе `tasks-data` и сохраняется при остановке или пересоздании контейнера. Чтобы остановить приложение, выполните команду ниже. Том с задачами останется на диске.

```powershell
docker compose down
```

## Запуск локально в Windows

Для локального запуска нужен Python 3.12. Команды вызывают интерпретатор из виртуального окружения напрямую.

```powershell
py -3.12 -m venv .venv-lab2
.\.venv-lab2\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-lab2\Scripts\python.exe -m uvicorn main:app --reload
```

SQLite создаст `data/tasks.db` при запуске. Переменная окружения `TSV_DB_PATH` позволяет указать другой путь.

## Проверка API

Запросы можно отправлять из PowerShell или другого HTTP-клиента на http://localhost:8000. Для POST укажите заголовок Content-Type: application/json. Схема API доступна в [openapi.json](http://localhost:8000/openapi.json).

| Шаг | Запрос | Ожидаемый результат |
| --- | --- | --- |
| 1 | `POST /tasks` с JSON ниже | `201 Created`, объект задачи с `id` и заголовок `Location` |
| 2 | `GET /tasks` | `200 OK`, созданная задача в списке |
| 3 | `GET /tasks/{task_id}` с полученным `id` | `200 OK`, объект задачи |
| 4 | `POST /tasks` с `priority: 0` или заголовком из пробелов | `422 Unprocessable Entity`, ошибки валидации |
| 5 | `docker compose down`, затем `docker compose up -d` и повтор шага 3 | `200 OK`, задача сохранилась |
| 6 | `DELETE /tasks/{task_id}` с тем же `id` | `204 No Content`, пустое тело |
| 7 | Повторить шаг 3 или 6 | `404 Not Found`, JSON с полем `detail` |

```json
{
  "title": "Подготовить ЛР2",
  "description": "Проверить запросы к API",
  "priority": 3,
  "completed": false
}
```

Поле `title` обязательно. После удаления пробелов в начале и конце в нём должно остаться от 1 до 100 символов. `description` допускает до 500 символов, по умолчанию это пустая строка. `priority` принимает целые числа от 1 до 5 и по умолчанию равно 3, а `completed` принимает логическое значение и по умолчанию равно `false`. Неизвестные поля и неверные типы отклоняются. `id` присваивает сервер.
