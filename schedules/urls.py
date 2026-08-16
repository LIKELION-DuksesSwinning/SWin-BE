from django.urls import path
from .views import *

urlpatterns = [
    path('', ScheduleListCreateView.as_view(), name='schedule-list-create'),
    path('<int:schedule_id>/', ScheduleDetailView.as_view(), name='schedule-detail'),
]