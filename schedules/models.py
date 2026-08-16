from django.db import models
from django.conf import settings

class Schedule(models.Model):
    CATEGORY_CHOICES = (
        ('SWIM', '수영'),
        ('CLINIC', '클리닉'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedules')
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    memo = models.TextField(null=True, blank=True)
    is_repeat = models.BooleanField(default=False)
    repeat_option = models.CharField(max_length=50, null=True, blank=True, help_text="주마다 반복 등")
    
    # 🦁 clinic 앱과의 연동을 위한 외래키 (Null 허용)
    clinic_reservation = models.ForeignKey(
        'clinic.ClinicReservation', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='schedules'
    ) 