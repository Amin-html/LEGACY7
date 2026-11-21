from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


def mine(request):
    # Чужие уведомления недоступны ни по какому ID: для них просто 404
    return Notification.objects.filter(user=request.user)


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = []

    def get_queryset(self):
        qs = mine(self.request)
        if self.request.query_params.get("unread", "").lower() in ("1", "true"):
            qs = qs.filter(is_read=False)
        return qs


class UnreadCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"unread": mine(request).filter(is_read=False).count()})


class MarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(mine(request), pk=pk)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class ReadAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        updated = mine(request).filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})