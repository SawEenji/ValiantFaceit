#!/usr/bin/env bash
set -euo pipefail

# Инициализация БД
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
