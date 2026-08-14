from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import WeeklyReport
from .serializers import WeeklyReportSerializer, WeeklyReportListSerializer


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
