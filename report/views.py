from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RoutineRecommendation, WeeklyReport
from .serializers import RoutineRecommendationSerializer, WeeklyReportSerializer, WeeklyReportListSerializer


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


class RoutineRecommendationLatestView(APIView):
    """GET /api/v1/reports/routines/latest/ — 2.3.1 최신 수영 루틴 추천"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        routine = (
            RoutineRecommendation.objects.filter(weekly_report__user=request.user)
            .order_by("-weekly_report__week_start")
            .first()
        )
        if not routine:
            return Response({"error": {"code": "NOT_FOUND", "message": "아직 생성된 루틴 추천이 없습니다."}}, status=404)
        return Response(RoutineRecommendationSerializer(routine).data)
