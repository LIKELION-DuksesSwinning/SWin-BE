from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL



class Clinic(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class ClinicReservation(models.Model):
    class Status(models.TextChoices):
        RECOMMENDED = "recommended", "권장됨"
        BOOKED = "booked", "예약됨"
        COMPLETED = "completed", "방문 완료"
        CANCELLED = "cancelled", "취소됨"

    class TriggerReason(models.TextChoices):
        SCORE_STREAK = "score_streak", "증상 점수 연속 3회 이상 상승"
        PHOTO_DIFF_SEVERE = "photo_diff_severe", "얼굴 사진에서 수영 전후 차이가 심함"


    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clinic_reservations')
    user_consented = models.BooleanField(default=False, verbose_name="자료 전달 동의 여부")
    user_note = models.TextField(blank=True, verbose_name="사용자 기타 메모(요청사항)")

    trigger_reason = models.CharField(max_length=20, choices=TriggerReason.choices, null=True, blank=True)
    trigger_swim_record_ids = models.JSONField(default=list, blank=True)

    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='reservations', null=True)
    visit_date = models.DateField(null=True, blank=True)
    visit_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECOMMENDED)

    # 방문 후 클리닉 직원/SWin 관리자가 Django admin에서 직접 입력 (외부 클리닉 시스템 연동 없음)
    treatment_items = models.JSONField(default=list, blank=True, verbose_name="시술 내역")

    calendar_synced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["clinic", "visit_date", "visit_time"],
                condition=models.Q(status="booked"),
                name="unique_booked_clinic_slot",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.clinic} - {self.visit_date}"