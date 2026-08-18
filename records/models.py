from django.conf import settings
from django.db import models

class SwimRecord(models.Model):
    TIMING_CHOICES = (
        ('BEFORE', '수영 전'),
        ('AFTER', '수영 후'),
        ('ADD', '추가 기록'),
    )

    SWIM_TIME_CHOICES = (
        ('30분 미만', '30분 미만'),
        ('30~60분', '30~60분'),
        ('60~90분', '60~90분'),
        ('90분 이상', '90분 이상'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='swim_records'
    )
    schedule = models.ForeignKey(
        'schedules.Schedule', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='swim_records'
    )
    parent_record = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='additional_records',
        help_text="추가 기록일 경우 원본 수영 기록 참조"
    )
    timing = models.CharField(max_length=10, choices=TIMING_CHOICES)
    photo = models.ImageField(upload_to='swim_photos/%Y/%m/', null=True, blank=True)
    swim_time = models.CharField(max_length=20, choices=SWIM_TIME_CHOICES, null=True, blank=True)
    memo = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} - {self.get_timing_display()} ({self.created_at.strftime('%Y-%m-%d')})"


class SwimRecordSymptom(models.Model):
    SCORE_CHOICES = (
        ('상', '상'),
        ('중', '중'),
        ('하', '하'),
    )

    swim_record = models.ForeignKey(
        SwimRecord, 
        on_delete=models.CASCADE, 
        related_name='symptoms'
    )
    symptom_type = models.CharField(max_length=20, help_text="당김, 건조, 가려움, 붉음, 여드름 등")
    score = models.CharField(max_length=5, choices=SCORE_CHOICES)

    def __str__(self):
        return f"{self.symptom_type} ({self.score})"