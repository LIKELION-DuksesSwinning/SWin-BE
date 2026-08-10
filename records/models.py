from django.db import models
from django.conf import settings

# class SwimRecord(models.Model):   # pools 앱 모델 구현 후, 임시 주석
#     TIMING_CHOICES = (
#         ('BEFORE', '수영 전'),
#         ('AFTER', '수영 후'),
#         ('ADD', '기록 추가'),
#     )
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='swim_records')
#     schedule = models.ForeignKey('schedules.Schedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='swim_records')
#     pool = models.ForeignKey('pools.Pool', on_delete=models.SET_NULL, null=True, blank=True, related_name='swim_records') # 팀원 Pool 참조
    
#     timing = models.CharField(max_length=10, choices=TIMING_CHOICES)
#     photo = models.ImageField(upload_to='swim_photos/', null=True, blank=True)
#     swim_time = models.PositiveIntegerField(null=True, blank=True, help_text="분 단위")
#     memo = models.TextField(null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)

# class SwimRecordSymptom(models.Model):
#     SCORE_CHOICES = (
#         ('HIGH', '상'),
#         ('MID', '중'),
#         ('LOW', '하'),
#     )
#     swim_record = models.ForeignKey(SwimRecord, on_delete=models.CASCADE, related_name='symptoms')
#     symptom_type = models.CharField(max_length=20) # 당김, 건조, 가려움, 붉음, 트러블
#     score = models.CharField(max_length=5, choices=SCORE_CHOICES)