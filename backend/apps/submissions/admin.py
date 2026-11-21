from django.contrib import admin

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("title", "contest", "author", "status", "submitted_at")
    list_filter = ("status",)
    search_fields = ("title", "author__email", "author__username")
    raw_id_fields = ("contest", "author")