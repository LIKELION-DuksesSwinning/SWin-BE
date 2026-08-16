from django.urls import path
from .views import NotificationListView, NotificationReadView

urlpatterns = [
    # 1.3 알림 목록 조회
    path('', NotificationListView.as_view(), name='notification-list'),
    # 1.3 특정 알림 읽음 처리
    path('<int:notification_id>/read/', NotificationReadView.as_view(), name='notification-read'),
]