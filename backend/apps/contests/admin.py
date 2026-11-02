from django.contrib import admin

from .models import Category, Contest, ContestJury, JudgingCriterion, Prize


class PrizeInline(admin.TabularInline):
    model = Prize
    extra = 1


class CriterionInline(admin.TabularInline):
    model = JudgingCriterion
    extra = 1


class JuryInline(admin.TabularInline):
    model = ContestJury
    extra = 1
    raw_id_fields = ("judge",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "organizer", "status", "starts_at", "deadline")
    list_filter = ("status", "category")
    search_fields = ("title", "description")
    raw_id_fields = ("organizer",)
    inlines = [PrizeInline, CriterionInline, JuryInline]