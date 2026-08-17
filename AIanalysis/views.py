from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Analysis
from .serializers import AnalysisCreateSerializer, AnalysisDetailSerializer, AnalysisListSerializer
from .services import run_skin_analysis


class AnalysisListCreateView(generics.ListCreateAPIView):
    """
    POST /api/v1/analysis/skin/                       - 2.1.1 AI 피부 진단 실행
    GET  /api/v1/analysis/skin/?swim_record_id={id}   - 2.1.2 분석 이력 목록
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Analysis.objects.filter(user=self.request.user)
        swim_record_id = self.request.query_params.get("swim_record_id")
        if swim_record_id:
            qs = qs.filter(swim_record_id=swim_record_id)
        return qs

    def get_serializer_class(self):
        return AnalysisCreateSerializer if self.request.method == "POST" else AnalysisListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                {"error": {"code": "VALIDATION_ERROR", "fields": serializer.errors}},
                status=422,
            )

        swim_record = serializer.context["swim_record"]

        try:
            analysis = run_skin_analysis(request.user, swim_record)
        except Exception as e:
            return Response(
                {"error": {"code": "AI_SERVICE_ERROR", "message": str(e)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(AnalysisDetailSerializer(analysis).data, status=status.HTTP_201_CREATED)


class AnalysisDetailView(generics.RetrieveAPIView):
    """GET /api/v1/analysis/{analysisId}/  - 2.1.2 분석 결과 상세 조회"""

    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisDetailSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)
