from django.db import OperationalError, connection
from django.http import JsonResponse


def health(request):
    """Проверка для Docker и хостинга: приложение живо и база отвечает."""
    try:
        connection.ensure_connection()
    except OperationalError:
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})