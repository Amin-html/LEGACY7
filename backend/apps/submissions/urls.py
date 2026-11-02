from django.urls import path
from rest_framework.routers import SimpleRouter

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
] + router.urls