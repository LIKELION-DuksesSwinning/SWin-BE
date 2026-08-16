import datetime

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Clinic, ClinicReservation
from .serializer import (
    ClinicReferralConsentSerializer,
    ClinicReferralListSerializer,
    ClinicReservationCreateSerializer,
    ClinicReservationDetailSerializer,
    ClinicReservationListSerializer,
    ClinicReservationUpdateSerializer,
    ClinicSerializer,
)


class ClinicListView(generics.ListAPIView):
    """GET /api/v1/clinics/?district={district} — 4.2 제휴 클리닉 목록"""

    permission_classes = [IsAuthenticated]
    serializer_class = ClinicSerializer

    def get_queryset(self):
        qs = Clinic.objects.all()
        district = self.request.query_params.get("district")
        if district:
            qs = qs.filter(district=district)
        return qs


class ClinicAvailableTimesView(APIView):
    """
    GET /api/v1/clinics/{clinic_id}/available-times/?date=YYYY-MM-DD
    — 4.2 시간대 선택 화면: 해당 클리닉·날짜에 이미 예약(booked)된 시간 목록.
    프론트는 자체 고정 시간표(예: 10:00~21:00, 15분 단위)에서 이 목록에 포함된 시간을 비활성 처리하면 됨.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, clinic_id):
        clinic = get_object_or_404(Clinic, pk=clinic_id)

        date_str = request.query_params.get("date")
        if not date_str:
            return Response({"error": {"code": "VALIDATION_ERROR", "message": "date 쿼리 파라미터가 필요합니다."}}, status=400)
        try:
            visit_date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({"error": {"code": "VALIDATION_ERROR", "message": "date는 YYYY-MM-DD 형식이어야 합니다."}}, status=400)

        booked_times = (
            ClinicReservation.objects.filter(
                clinic=clinic, visit_date=visit_date, status=ClinicReservation.Status.BOOKED
            )
            .order_by("visit_time")
            .values_list("visit_time", flat=True)
        )

        return Response({
            "clinicId": clinic.id,
            "date": date_str,
            "bookedTimes": [t.strftime("%H:%M") for t in booked_times],
        })


class ClinicReferralListView(generics.ListAPIView):
    """GET /api/v1/clinics/referrals/ — 4.1 권장 목록 (status=recommended 고정)"""

    permission_classes = [IsAuthenticated]
    serializer_class = ClinicReferralListSerializer

    def get_queryset(self):
        return ClinicReservation.objects.filter(
            user=self.request.user, status=ClinicReservation.Status.RECOMMENDED
        )


class ClinicReferralConsentView(APIView):
    """PATCH /api/v1/clinics/referrals/{referral_id}/consent/ — 4.1 동의 처리"""

    permission_classes = [IsAuthenticated]

    def patch(self, request, referral_id):
        try:
            referral = ClinicReservation.objects.get(pk=referral_id, user=request.user)
        except ClinicReservation.DoesNotExist:
            return Response({"error": {"code": "NOT_FOUND"}}, status=404)

        serializer = ClinicReferralConsentSerializer(referral, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ClinicReservationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/v1/clinics/reservations/  — 4.3 예약 내역 목록
    POST /api/v1/clinics/reservations/  — 4.2 신규 예약 생성 (권장 없이 사용자가 직접)
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClinicReservation.objects.filter(user=self.request.user).select_related("clinic")

    def get_serializer_class(self):
        return (
            ClinicReservationCreateSerializer
            if self.request.method == "POST"
            else ClinicReservationListSerializer
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        return Response(
            ClinicReservationDetailSerializer(reservation).data,
            status=status.HTTP_201_CREATED,
        )


class ClinicReservationDetailUpdateView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/clinics/reservations/{id}/  — 4.3 예약 상세
    PATCH /api/v1/clinics/reservations/{id}/  — 4.2 예약 확정 또는 취소
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClinicReservation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return (
            ClinicReservationUpdateSerializer
            if self.request.method == "PATCH"
            else ClinicReservationDetailSerializer
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        return Response(ClinicReservationDetailSerializer(reservation).data)

