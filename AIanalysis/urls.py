from django.urls import path

from .views import AnalysisDetailView, AnalysisListCreateView

urlpatterns = [
    path("skin/", AnalysisListCreateView.as_view(), name="analysis-list-create"),
    path("skin/<int:pk>/", AnalysisDetailView.as_view(), name="analysis-detail"),
]