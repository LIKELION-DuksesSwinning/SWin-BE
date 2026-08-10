from django.conf import settings
from django.db import models
from pools.models import Pool


class SwimRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='swim_records')
    pool = models.ForeignKey(Pool, on_delete=models.SET_NULL, null=True, related_name='swim_records')
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()

    class Meta:
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.user} - {self.date}"


class SkinRecord(models.Model):
    class Timing(models.TextChoices):
        BEFORE = 'before', '수영 전'
        AFTER = 'after', '수영 후'
        ADDITIONAL = 'additional', '추가 기록'

    class SymptomType(models.TextChoices):
        REDNESS = 'redness', '붉음 반응형'
        DRY = 'dry', '건조·당김형'
        ITCHY = 'itchy', '가려움 반응형'
        TROUBLE = 'trouble', '트러블 반응형'
        NONE = 'none', '이상 없음'
        NEEDS_CHECK = 'needs_check', '전문 확인 필요'

    swim_record = models.ForeignKey(SwimRecord, on_delete=models.CASCADE, related_name='skin_records')
    timing = models.CharField(max_length=20, choices=Timing.choices)
    symptom_type = models.CharField(max_length=20, choices=SymptomType.choices)
    symptom_level = models.PositiveSmallIntegerField()  # 1~5 등 점수
    memo = models.TextField(blank=True)
    photo = models.ImageField(upload_to='skin_records/%Y/%m/', blank=True, null=True)

    def __str__(self):
        return f"{self.swim_record} - {self.get_timing_display()}"