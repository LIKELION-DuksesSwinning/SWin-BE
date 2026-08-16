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
        return ClinicReservation.objects.filter(user=self.request.user)

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

