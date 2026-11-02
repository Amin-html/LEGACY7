from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce
from rest_framework import generics, permissions

from .filters import ContestFilter
from .models import Category, Contest
from .serializers import (
    CategorySerializer,
    ContestDetailSerializer,
    ContestListSerializer,
)


def public_contests():
    return (
        Contest.objects.filter(status__in=Contest.PUBLIC_STATUSES)
        .select_related("category", "organizer")
        .annotate(
            prize_pool=Coalesce(
                Sum("prizes__amount"),
                0,
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    filter_backends = []


class ContestListView(generics.ListAPIView):
    serializer_class = ContestListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ContestFilter
    search_fields = ("title", "description", "category__name")
    ordering_fields = ("deadline", "starts_at", "created_at", "prize_pool")
    ordering = ("-starts_at",)

    def get_queryset(self):
        return public_contests()


class ContestDetailView(generics.RetrieveAPIView):
    serializer_class = ContestDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"

    def get_queryset(self):
        return public_contests().prefetch_related("prizes", "criteria")