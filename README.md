# ValiantFaceit

Минимальный MVP платформы Faceit для Valorant Mobile.

Локальный запуск (Docker):

1. Скопируйте `.env.example` в `.env` и отредактируйте значения.
2. Соберите и запустите контейнеры:

```bash
docker-compose up --build -d
```

Сервис будет доступен по порту 5000.

Деплой на Railway (автоматически при push):

1. В репозитории на GitHub добавьте секрет `RAILWAY_API_KEY` (Settings → Secrets).
2. При push в `main` workflow `deploy_railway.yml` попытается выполнить `railway up`.

Примечание: сначала проверьте локально, миграции выполняются автоматически при старте контейнера.

ValiantFaceit Valorant Mobile
