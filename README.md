# LEGACY 7

Платформа онлайн-конкурсов: участники подают работы, жюри оценивает, система строит рейтинг.

## Стек
- Backend: Python 3.13, Django 5.2, Django REST Framework, PostgreSQL, SimpleJWT
- Frontend: Next.js, TypeScript, Tailwind CSS, Motion (в разработке)
- DevOps: Docker Compose, GitHub Actions (ruff, миграции, pytest)

## Быстрый старт (Windows PowerShell)

    Copy-Item .env.example .env
    notepad .env                      # задай DJANGO_SECRET_KEY и POSTGRES_PASSWORD
    docker compose up -d db redis
    python -m venv backend\.venv
    .\backend\.venv\Scripts\Activate.ps1
    pip install -r backend\requirements-dev.txt
    python backend\manage.py migrate
    python backend\manage.py createsuperuser
    python backend\manage.py seed_demo
    python backend\manage.py runserver

API: http://localhost:8000/api/v1/, админка: http://localhost:8000/admin/.
Демо-организатор: organizer@legacy7.local / Demo-Pass-123 (создаёт seed_demo, только при DEBUG=True).

## Всё в Docker

    docker compose up -d --build

Поднимает PostgreSQL, Redis и backend. Миграции выполняются при старте. Порт 8000 должен быть свободен.

## Тесты и линтер

    python -m pytest backend
    ruff check backend
    python backend\manage.py makemigrations --check --dry-run

## Переменные окружения
Полный список в .env.example. Секреты хранятся только в .env (в Git не попадает).

- DJANGO_SECRET_KEY: длинная случайная строка, подписывает токены
- POSTGRES_*: доступ к базе
- GOOGLE_CLIENT_ID: для входа через Google (client secret при ID-token потоке не нужен)
- FRONTEND_URL: куда ведут ссылки из писем
- SUBMISSION_FILE_MAX_MB, COVER_MAX_MB: лимиты загрузок

## Роли
participant, jury, organizer, admin. Права проверяются на сервере. Роли jury и admin выдаёт только администратор.

## Жизненный цикл конкурса
draft, published, judging, finished. Архив доступен для черновиков и опубликованных конкурсов.
Завершённый конкурс остаётся в рейтинге.

## Безопасность
- refresh-токен только в httpOnly-cookie, access живёт 15 минут
- файлы проверяются по содержимому, хранятся вне публичной папки и отдаются через API с проверкой прав
- чужие объекты отдают 404, а не 403
- рейтинг считается на сервере по подтверждённым оценкам жюри

## Статус
Backend: auth, конкурсы, организатор, работы и файлы, жюри, рейтинг, уведомления.
Дальше: frontend и деплой.