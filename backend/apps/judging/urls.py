from django.urls import path

from .views import (
    EvaluationView,
    FinalizeEvaluationView,
    JuryContestListView,
    JurySubmissionDetailView,
    JurySubmissionListView,
)

urlpatterns = [
    path("jury/contests/", JuryContestListView.as_view(), name="jury-contest-list"),
    path("jury/submissions/", JurySubmissionListView.as_view(), name="jury-submission-list"),
    path("jury/submissions/<int:pk>/", JurySubmissionDetailView.as_view(), name="jury-submission-detail"),
    path("jury/submissions/<int:pk>/evaluation/", EvaluationView.as_view(), name="jury-evaluation"),
    path(
        "jury/submissions/<int:pk>/evaluation/finalize/",
        FinalizeEvaluationView.as_view(),
        name="jury-evaluation-finalize",
    ),
]