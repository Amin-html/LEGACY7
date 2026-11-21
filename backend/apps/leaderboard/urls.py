from django.urls import path

from .views import ContestResultsView, LeaderboardView, MySubmissionResultView

urlpatterns = [
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("contests/<str:slug>/results/", ContestResultsView.as_view(), name="contest-results"),
    path(
        "me/submissions/<int:pk>/result/",
        MySubmissionResultView.as_view(),
        name="my-submission-result",
    ),
]