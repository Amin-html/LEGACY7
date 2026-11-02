from django.urls import path

from .views import CategoryListView, ContestDetailView, ContestListView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="category-list"),
    path("contests/", ContestListView.as_view(), name="contest-list"),
    # str, а не slug: slug-конвертер Django не понимает кириллицу
    path("contests/<str:slug>/", ContestDetailView.as_view(), name="contest-detail"),
]