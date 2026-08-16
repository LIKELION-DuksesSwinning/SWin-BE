from django.utils import timezone
from rest_framework import serializers

from .models import Clinic, ClinicReservation


def _has_booking_conflict(clinic, visit_date, visit_time, exclude_pk=None):
    qs = ClinicReservation.objects.filter(
        clinic=clinic,
        visit_date=visit_date,
        visit_time=visit_time,
        status=ClinicReservation.Status.BOOKED,
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs.exists()


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id", "name", "district", "phone"]


class ClinicMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinic
        fields = ["id", "name"]


class ClinicReferralListSerializer(serializers.ModelSerializer):
    triggerReasonDisplay = serializers.CharField(source="get_trigger_reason_display", read_only=True)

    class Meta:
        model = ClinicReservation
        fields = [
            "id", "status", "trigger_reason", "triggerReasonDisplay",
            "trigger_swim_record_ids", "user_consented", "user_note", "created_at",
        ]


class ClinicReferralConsentSerializer(serializers.ModelSerializer):
    """4.1 PATCH /clinics/referrals/{referral_id}/consent/"""

    class Meta:
        model = ClinicReservation
        fields = ["id", "user_consented", "user_note"]
        read_only_fields = ["id"]


class ClinicReservationListSerializer(serializers.ModelSerializer):
    """4.3 GET /clinics/reservations/ 목록"""

    statusDisplay = serializers.CharField(source="get_status_display", read_only=True)
    clinicName = serializers.CharField(source="clinic.name", read_only=True, default=None)

    class Meta:
        model = ClinicReservation
        fields = [
            "id", "status", "statusDisplay", "clinicName",
            "visit_date", "visit_time", "treatment_items", "created_at",
        ]


class ClinicReservationDetailSerializer(serializers.ModelSerializer):
    """4.3 GET /clinics/reservations/{id}/ 상세, 4.2 PATCH/POST 응답 공용"""

    clinic = ClinicMiniSerializer(read_only=True)
    statusDisplay = serializers.CharField(source="get_status_display", read_only=True)
    triggerReasonDisplay = serializers.CharField(source="get_trigger_reason_display", read_only=True)

    class Meta:
        model = ClinicReservation
        fields = [
            "id", "clinic", "status", "statusDisplay", "trigger_reason", "triggerReasonDisplay",
            "trigger_swim_record_ids", "user_consented", "user_note",
            "visit_date", "visit_time", "treatment_items", "calendar_synced", "created_at",
        ]


class ClinicReservationCreateSerializer(serializers.ModelSerializer):
    """4.2 POST /clinics/reservations/ — 권장 없이 사용자가 직접 새 예약 생성"""

    clinic_id = serializers.PrimaryKeyRelatedField(
        source="clinic", queryset=Clinic.objects.all(), write_only=True
    )

    class Meta:
        model = ClinicReservation
        fields = ["clinic_id", "visit_date", "visit_time", "user_note", "user_consented"]

    def validate(self, attrs):
        if not attrs.get("user_consented"):
            raise serializers.ValidationError({"userConsented": "자료 전달 동의가 필요합니다."})

        visit_date = attrs.get("visit_date")
        visit_time = attrs.get("visit_time")

        if visit_date and visit_date < timezone.localdate():
            raise serializers.ValidationError({"visitDate": "지난 날짜로는 예약할 수 없습니다."})

        if visit_date and visit_time and _has_booking_conflict(attrs.get("clinic"), visit_date, visit_time):
            raise serializers.ValidationError({"visitTime": "이미 예약된 시간대입니다."})

        return attrs

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        validated_data["status"] = ClinicReservation.Status.BOOKED
        validated_data["calendar_synced"] = True  # TODO: 실제 캘린더 연동 로직 붙으면 교체
        return super().create(validated_data)


class ClinicReservationUpdateSerializer(serializers.ModelSerializer):
    """
    4.2 PATCH /clinics/reservations/{id}/ — '예약 확정'과 '예약 취소' 둘 다 이 하나로 처리.
    요청 body에 status="cancelled"가 오면 취소 처리,
    visit_date/visit_time(+user_consented)이 오면 예약 확정 처리.
    """

    class Meta:
        model = ClinicReservation
        fields = ["status", "visit_date", "visit_time", "user_note", "user_consented"]
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate(self, attrs):
        status_value = attrs.get("status")

        # 이 엔드포인트로는 취소(cancelled) 외의 상태를 직접 지정할 수 없음.
        # (booked는 visit_date/visit_time 제공으로, completed는 별도 절차로 처리)
        if status_value is not None and status_value != ClinicReservation.Status.CANCELLED:
            raise serializers.ValidationError(
                {"status": "이 API에서는 취소(cancelled) 상태만 직접 지정할 수 있습니다."}
            )

        # 취소 요청인 경우: 이미 완료/취소된 예약은 취소 불가
        if status_value == ClinicReservation.Status.CANCELLED:
            if self.instance and self.instance.status in (
                ClinicReservation.Status.COMPLETED,
                ClinicReservation.Status.CANCELLED,
            ):
                raise serializers.ValidationError(
                    {"status": "이미 완료되었거나 취소된 예약은 취소할 수 없습니다."}
                )
            return attrs

        # 예약 확정 요청인 경우: 방문일/시간이 있으면 동의 필수 + 과거 날짜/중복 예약 검증
        if attrs.get("visit_date") or attrs.get("visit_time"):
            consented = attrs.get("user_consented", self.instance.user_consented if self.instance else False)
            if not consented:
                raise serializers.ValidationError({"userConsented": "자료 전달 동의가 필요합니다."})

            visit_date = attrs.get("visit_date", self.instance.visit_date if self.instance else None)
            visit_time = attrs.get("visit_time", self.instance.visit_time if self.instance else None)

            if visit_date and visit_date < timezone.localdate():
                raise serializers.ValidationError({"visitDate": "지난 날짜로는 예약할 수 없습니다."})

            if visit_date and visit_time:
                clinic = self.instance.clinic if self.instance else None
                exclude_pk = self.instance.pk if self.instance else None
                if _has_booking_conflict(clinic, visit_date, visit_time, exclude_pk=exclude_pk):
                    raise serializers.ValidationError({"visitTime": "이미 예약된 시간대입니다."})
        return attrs

    def update(self, instance, validated_data):
        if validated_data.get("status") == ClinicReservation.Status.CANCELLED:
            instance.status = ClinicReservation.Status.CANCELLED
            instance.save(update_fields=["status", "updated_at"])
            return instance

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if instance.visit_date and instance.visit_time:
            instance.status = ClinicReservation.Status.BOOKED
            instance.calendar_synced = True  # TODO: 실제 캘린더 연동 로직 붙으면 교체

        instance.save()
        return instance