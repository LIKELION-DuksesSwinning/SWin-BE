from django.urls import path

from .views import (
    RoutineRecommendationLatestView,
    WeeklyReportDetailView,
    WeeklyReportLatestView,
    WeeklyReportListView,
)

urlpatterns = [
    path("weekly/latest/", WeeklyReportLatestView.as_view(), name="weekly-report-latest"),
    path("weekly/", WeeklyReportListView.as_view(), name="weekly-report-list"),
    path("weekly/<int:pk>/", WeeklyReportDetailView.as_view(), name="weekly-report-detail"),
    path("routines/latest/", RoutineRecommendationLatestView.as_view(), name="routine-recommendation-latest"),
]