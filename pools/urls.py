from django.urls import path

from .views import Region, Pool

urlpatterns = [
    path("
    path("reports/weekly/", WeeklyReportListView.as_view(), name="weekly-report-list"),
    path("reports/weekly/<int:pk>/", WeeklyReportDetailView.as_view(), name="weekly-report-detail"),
]