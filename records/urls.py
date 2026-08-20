from django.urls import path
from .views import (
    SwimRecordListCreateView,
    SwimRecordDetailView,
    AdditionalSkinRecordCreateView
)

urlpatterns = [
    # 1.2.1 / 1.2.2 수영 기록 등록 및 조회
    path('swim/', SwimRecordListCreateView.as_view(), name='swim-record-list-create'),
    # 1.2.4 이전 기록 상세 확인 및 수정
    path('swim/<int:record_id>/', SwimRecordDetailView.as_view(), name='swim-record-detail'),
    # 1.2.3 추가 기록 등록
    path('swim/<int:record_id>/additional/', AdditionalSkinRecordCreateView.as_view(), name='swim-record-additional'),
]