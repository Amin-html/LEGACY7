import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Contest


class ContestFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name="category__slug")
    status = django_filters.ChoiceFilter(choices=Contest.Status.choices)
    deadline_after = django_filters.IsoDateTimeFilter(field_name="deadline", lookup_expr="gte")
    deadline_before = django_filters.IsoDateTimeFilter(field_name="deadline", lookup_expr="lte")
    open = django_filters.BooleanFilter(method="filter_open")

    class Meta:
        model = Contest
        fields = []

    def filter_open(self, queryset, name, value):
        """open=true: конкурсы, которые принимают работы сейчас. open=false: все остальные."""
        now = timezone.now()
        open_q = Q(status=Contest.Status.PUBLISHED, starts_at__lte=now, deadline__gt=now)
        return queryset.filter(open_q) if value else queryset.exclude(open_q)