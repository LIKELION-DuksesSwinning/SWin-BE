from django.urls import path

from .views import WeeklyReportDetailView, WeeklyReportLatestView, WeeklyReportListView

urlpatterns = [
    path("reports/weekly/latest/", WeeklyReportLatestView.as_view(), name="weekly-report-latest"),
    path("reports/weekly/", WeeklyReportListView.as_view(), name="weekly-report-list"),
    path("reports/weekly/<int:pk>/", WeeklyReportDetailView.as_view(), name="weekly-report-detail"),
]