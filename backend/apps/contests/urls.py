from django.urls import path
from rest_framework.routers import SimpleRouter

from .manage_views import ManageContestViewSet
from .views import CategoryListView, ContestDetailView, ContestListView

router = SimpleRouter()
router.register("manage/contests", ManageContestViewSet, basename="manage-contest")

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("contests/", ContestListView.as_view(), name="contest-list"),
    # str, а не slug: slug-конвертер Django не понимает кириллицу
    path("contests/<str:slug>/", ContestDetailView.as_view(), name="contest-detail"),
] + router.urls