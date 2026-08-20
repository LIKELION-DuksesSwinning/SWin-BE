from django.db import models
from django.conf import settings

class Notification(models.Model):
    CATEGORY_CHOICES = (
        ('SWIM_RECORD', '수영 후 기록'),
        ('SWIM_SCHEDULE', '수영 예정'),
        ('CLINIC', '클리닉 예약'),
        ('REPORT', '주간 리포트'),
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=100)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)