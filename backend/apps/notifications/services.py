from .models import Notification


def notify(user, kind, title, text="", **data):
    """Одно уведомление. data: ссылки для фронта (contest_slug, submission_id)."""
    return Notification.objects.create(user=user, kind=kind, title=title, text=text, data=data)


def notify_bulk(rows, kind, title, text=""):
    """Много уведомлений одним запросом. rows: список пар (пользователь, data)."""
    return Notification.objects.bulk_create(
        [Notification(user=user, kind=kind, title=title, text=text, data=data) for user, data in rows]
    )