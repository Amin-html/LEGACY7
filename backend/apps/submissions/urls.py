from django.urls import path
from rest_framework.routers import SimpleRouter

from .file_views import SubmissionFileDownloadView, SubmissionFileUploadView
from .views import (
    ManageContestSubmissionsView,
    ModerateSubmissionView,
    MySubmissionViewSet,
    PublicSubmissionListView,
)

router = SimpleRouter()
router.register("me/submissions", MySubmissionViewSet, basename="my-submission")

urlpatterns = [
    path(
        "contests/<str:slug>/submissions/",
        PublicSubmissionListView.as_view(),
        name="contest-submissions",
    ),
    path(
        "manage/contests/<int:contest_id>/submissions/",
        ManageContestSubmissionsView.as_view(),
        name="manage-contest-submissions",
    ),
    path(
        "manage/submissions/<int:pk>/moderate/",
        ModerateSubmissionView.as_view(),
        name="manage-submission-moderate",
    ),
    path(
        "me/submissions/<int:pk>/file/",
        SubmissionFileUploadView.as_view(),
        name="my-submission-file",
    ),
    path("submissions/<int:pk>/file/", SubmissionFileDownloadView.as_view(), name="submission-file"),
] + router.urls