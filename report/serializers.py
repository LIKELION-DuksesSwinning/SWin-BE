# ==========================================================
# report/serializers.py
# ==========================================================
from rest_framework import serializers

from .models import RoutineRecommendation, WeeklyReport


class RoutineRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutineRecommendation
        fields = ["id", "recommended_swim_count", "recommended_swim_minutes", "skin_care_routine"]


class WeeklyReportSerializer(serializers.ModelSerializer):
    routine = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyReport
        fields = [
            "id", "week_start", "week_end", "swim_count", "avg_swim_duration",
            "symptom_trend", "recommended_ingredients", "recommended_products",
            "clinic_recommended", "other_pool_recommended", "routine", "generated_at",
        ]

    def get_routine(self, obj):
        routine = getattr(obj, "routine", None)
        return RoutineRecommendationSerializer(routine).data if routine else None


class WeeklyReportListSerializer(serializers.ModelSerializer):
    """목록용 (가벼운 버전)"""

    class Meta:
        model = WeeklyReport
        fields = ["id", "week_start", "week_end", "clinic_recommended"]


# ==========================================================
# report/views.py
# ==========================================================
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WeeklyReport
# from .serializers import WeeklyReportSerializer, WeeklyReportListSerializer  # 위에서 이미 정의됨


class WeeklyReportLatestView(APIView):
    """GET /api/v1/reports/weekly/latest/"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        report = (
            WeeklyReport.objects.filter(user=request.user)
            .order_by("-week_start")
            .first()
        )
        if not report:
            return Response({"error": {"code": "NOT_FOUND", "message": "아직 생성된 리포트가 없습니다."}}, status=404)
        return Response(WeeklyReportSerializer(report).data)


class WeeklyReportListView(generics.ListAPIView):
    """GET /api/v1/reports/weekly/"""

    permission_classes = [IsAuthenticated]
    serializer_class = WeeklyReportListSerializer

    def get_queryset(self):
        return WeeklyReport.objects.filter(user=self.request.user)


class WeeklyReportDetailView(generics.RetrieveAPIView):
    """GET /api/v1/reports/weekly/{reportId}/"""

    permission_classes = [IsAuthenticated]
    serializer_class = WeeklyReportSerializer

    def get_queryset(self):
        return WeeklyReport.objects.filter(user=self.request.user)



