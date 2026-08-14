from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class WeeklyReport(models.Model):
    """주간 수영 리포트 (2.2.1)"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="weekly_reports")
    week_start = models.DateField()
    week_end = models.DateField()

    swim_count = models.PositiveIntegerField(default=0)
    avg_swim_duration = models.PositiveIntegerField(default=0)  # 분 단위

    # symptomTrend: [{"date": "2026-08-03", "symptomType": "dryness", "score": "mid"}, ...]
    symptom_trend = models.JSONField(default=list, blank=True)

    recommended_ingredients = models.JSONField(default=list, blank=True)  # ["세라마이드", "판테놀"]
    recommended_products = models.JSONField(default=list, blank=True)     # [{"name":..., "reason":...}]

    clinic_recommended = models.BooleanField(default=False)
    other_pool_recommended = models.BooleanField(default=False)

    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "week_start")
        ordering = ["-week_start"]

    def __str__(self):
        return f"{self.user} - {self.week_start}~{self.week_end}"


class RoutineRecommendation(models.Model):
    """수영 루틴 추천 (2.3) — WeeklyReport와 1:1"""

    weekly_report = models.OneToOneField(
        WeeklyReport, on_delete=models.CASCADE, related_name="routine"
    )
    recommended_swim_count = models.PositiveIntegerField()
    recommended_swim_minutes = models.PositiveIntegerField()

    intensity_note = models.CharField(max_length=100, null=True, blank=True)  # "회복 전까지 강도는 가볍게"
    condition_text = models.CharField(max_length=200, null=True, blank=True)  # "붉음이 2일 연속 감소하면 기존 루틴으로"

    # skinCareRoutine: [{"name": "보습 강화 루틴", "steps": ["미온수 샤워", "수분 크림 도포"]}]
    skin_care_routine = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.weekly_report} 루틴"
