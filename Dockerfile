# берем официальный легкий образ питона
FROM python:3.12-slim

WORKDIR /app

# отключаем создание pyc файлов и буферизацию логов uvicorn
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TSV_DB_PATH=/app/data/tasks.db

# создаем отдельного пользователя app чтобы не запускаться от рута
RUN groupadd --system app && useradd --system --gid app app \
    && mkdir -p /app/data && chown app:app /app/data

# зависимости ставим отдельным шагом чтобы докер кэшировал слой
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# копируем код приложения
COPY main.py ./

USER app
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
