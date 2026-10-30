# LEGACY 7

Платформа онлайн-конкурсов: участники подают работы, жюри оценивает, система строит рейтинг.

## Стек
- Frontend: Next.js (App Router), React, TypeScript, Tailwind CSS, Motion, Axios
- Backend: Django, Django REST Framework, PostgreSQL, Redis (+ Celery)
- Auth: email/password, Google OAuth, SimpleJWT
- DevOps: Docker Compose, GitHub Actions

## Быстрый старт (локально)

    Copy-Item .env.example .env
    docker compose up -d

## Структура
- `backend/` — Django API
- `frontend/` — Next.js приложение
- `docs/` — архитектура и заметки

## Статус
Этап 0: инфраструктура. Остальное в разработке.