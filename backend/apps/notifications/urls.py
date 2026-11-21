from django.urls import path

from .views import MarkReadView, NotificationListView, ReadAllView, UnreadCountView

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread-count/", UnreadCountView.as_view(), name="notification-unread-count"),
    path("notifications/read-all/", ReadAllView.as_view(), name="notification-read-all"),
    path("notifications/<int:pk>/read/", MarkReadView.as_view(), name="notification-read"),
]