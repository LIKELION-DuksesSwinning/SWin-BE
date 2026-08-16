import uuid
from django.db import models
from django.conf import settings

class Schedule(models.Model):
    CATEGORY_CHOICES = (
        ('SWIM', '수영'),
        ('CLINIC', '클리닉'),
    )
    REPEAT_END_CHOICES = (
        ('FOREVER', '계속 반복'),
        ('COUNT', '일정 횟수 반복'),
        ('UNTIL_DATE', '종료 날짜'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='schedules'
    )
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    memo = models.TextField(null=True, blank=True)

    # 반복 관련 필드
    is_repeat = models.BooleanField(default=False)
    repeat_group_id = models.UUIDField(null=True, blank=True, help_text="반복 일정 묶음 식별용 UUID")
    repeat_interval_weeks = models.PositiveIntegerField(default=1, null=True, blank=True, help_text="N주마다 반복")
    repeat_end_type = models.CharField(max_length=20, choices=REPEAT_END_CHOICES, null=True, blank=True)
    repeat_count = models.PositiveIntegerField(null=True, blank=True, help_text="반복 횟수")
    repeat_until = models.DateField(null=True, blank=True, help_text="반복 종료 날짜")

    # clinic 앱과의 연동을 위한 외래키
    clinic_reservation = models.ForeignKey(
        'clinic.ClinicReservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules'
    )

    class Meta:
        ordering = ['start_datetime']

    def __str__(self):
        return f"[{self.category}] {self.user} - {self.start_datetime}"