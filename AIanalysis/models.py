from django.conf import settings
from django.db import models
from .models import SwimRecord

User = settings.AUTH_USER_MODEL


class Analysis(models.Model):
    """AI 피부 분석 결과 (2.1)"""

    class TriggerReason(models.TextChoices):
        SCORE_STREAK = "score_streak", "증상 점수 연속 3회 이상 상승"
        PERSISTED_72H = "persisted_72h", "증상 72시간 이상 지속"
        RECURRING_2W = "recurring_2w", "최근 2주 내 반복 악화"
        PHOTO_DIFF_SEVERE = "photo_diff_severe", "얼굴 사진에서 수영 전후 차이가 심함"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="analyses")
    swim_record = models.ForeignKey(SwimRecord, on_delete=models.CASCADE, related_name="analyses")

    # GPT가 직접 판단하는 값
    pattern_types = models.JSONField(default=list)  # ["trouble_type", "redness_type"]
    pattern_description = models.TextField(blank=True)
    symptom_changes = models.JSONField(default=list)  # [{"symptomType": "redness", "before": 3, "after": 5}]

    # 백엔드가 규칙으로 계산해서 채우는 값
    four_week_trend = models.JSONField(default=list, blank=True)  # [{"symptomType": "redness", "trend": "worsened"}]
    clinic_recommended = models.BooleanField(default=False)
    clinic_trigger_reason = models.CharField(
        max_length=20, choices=TriggerReason.choices, null=True, blank=True
    )

    disclaimer = models.CharField(
        max_length=200, default="AI 분석은 참고용이며, 의료 진단을 대체하지 않습니다."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.swim_record} - {self.created_at:%Y-%m-%d}"