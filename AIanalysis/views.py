from datetime import date, timedelta

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
    GET  /api/v1/analysis/skin/?date=YYYY-MM-DD        - 특정 날짜에 이미 완료된 분석 조회
                                                          (프론트가 "AI 분석 받기" 버튼을 다시 안 띄우고
                                                          바로 결과를 보여줄 수 있도록)
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Analysis.objects.filter(user=self.request.user)
        swim_record_id = self.request.query_params.get("swim_record_id")
        if swim_record_id:
            qs = qs.filter(swim_record_id=swim_record_id)
        date_param = self.request.query_params.get("date")
        if date_param:
            qs = qs.filter(swim_record__schedule__start_datetime__date=date_param)
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

        self._refresh_weekly_report(request.user)
        self._create_clinic_referral_if_needed(request.user, analysis)

        return Response(AnalysisDetailSerializer(analysis).data, status=status.HTTP_201_CREATED)

    def _refresh_weekly_report(self, user):
        """분석이 성공적으로 쌓이면, 그 주의 SWin 리포트/루틴 추천을 즉시 갱신한다."""
        from report.services import generate_routine_recommendation, generate_weekly_report

        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        try:
            weekly_report = generate_weekly_report(user, week_start)
            generate_routine_recommendation(weekly_report, user)
        except Exception:
            pass  # 리포트 갱신 실패는 분석 결과 응답 자체를 막지 않는다

    def _create_clinic_referral_if_needed(self, user, analysis):
        """분석 결과 클리닉 방문이 권장되면, 클리닉 연계 권장 목록에 뜨도록 ClinicReservation을 만든다/갱신한다."""
        if not analysis.clinic_recommended:
            return

        from clinic.models import Clinic, ClinicReservation

        try:
            # 현재 제휴 클리닉은 한 곳뿐이라 추천 생성 시 바로 연결해둔다.
            clinic = Clinic.objects.first()

            existing = ClinicReservation.objects.filter(
                user=user, status=ClinicReservation.Status.RECOMMENDED
            ).first()
            if existing:
                existing.clinic = existing.clinic or clinic
                existing.trigger_reason = analysis.clinic_trigger_reason
                existing.trigger_swim_record_ids = [analysis.swim_record_id]
                existing.save(update_fields=["clinic", "trigger_reason", "trigger_swim_record_ids", "updated_at"])
            else:
                ClinicReservation.objects.create(
                    user=user,
                    clinic=clinic,
                    status=ClinicReservation.Status.RECOMMENDED,
                    trigger_reason=analysis.clinic_trigger_reason,
                    trigger_swim_record_ids=[analysis.swim_record_id],
                )
        except Exception:
            pass  # 추천 연계 실패는 분석 결과 응답 자체를 막지 않는다


class AnalysisDetailView(generics.RetrieveAPIView):
    """GET /api/v1/analysis/{analysisId}/  - 2.1.2 분석 결과 상세 조회"""

    permission_classes = [IsAuthenticated]
    serializer_class = AnalysisDetailSerializer

    def get_queryset(self):
        return Analysis.objects.filter(user=self.request.user)
