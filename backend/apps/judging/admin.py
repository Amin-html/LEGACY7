from django.contrib import admin

from .models import Evaluation, EvaluationScore


class ScoreInline(admin.TabularInline):
    model = EvaluationScore
    extra = 0


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ("submission", "judge", "status", "total", "finalized_at")
    list_filter = ("status",)
    raw_id_fields = ("submission", "judge")
    inlines = [ScoreInline]