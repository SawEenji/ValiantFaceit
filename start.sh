#!/usr/bin/env bash
set -euo pipefail

# Инициализация БД
echo "[start] Проверка доступности базы данных..."
python - <<PY
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

url = os.environ.get('DATABASE_URL')
engine = create_engine(url)
for i in range(30):
    try:
        with engine.connect():
            print('DB is ready')
            break
    except OperationalError as exc:
        print(f'DB unavailable, retry {i+1}/30: {exc}')
        time.sleep(2)
else:
    raise SystemExit('Cannot connect to database after retries')
PY

echo "[start] Миграции и инициализация базы данных..."
export FLASK_APP=app.py
flask db upgrade || true
python - <<PY
from app import init_db
init_db()
print('DB initialized')
PY

echo "[start] Запуск Gunicorn..."
exec gunicorn -b 0.0.0.0:${PORT:-5000} "app:app" --workers 3 --threads 2 --log-level info
