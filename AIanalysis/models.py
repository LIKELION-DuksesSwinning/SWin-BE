from django.db import models
from records.models import SwimRecord


class AIAnalysis(models.Model):
    class AnalysisType(models.TextChoices):
        REDNESS = 'redness', '붉음 반응형'
        DRY = 'dry', '건조·당김형'
        ITCHY = 'itchy', '가려움 반응형'
        TROUBLE = 'trouble', '트러블 반응형'
        NONE = 'none', '이상 없음'
        NEEDS_CHECK = 'needs_check', '전문 확인 필요'

    swim_record = models.ForeignKey(SwimRecord, on_delete=models.CASCADE, related_name='analyses')
    analysis_type = models.CharField(max_length=20, choices=AnalysisType.choices)
    change_summary = models.TextField()  # 수영 전후 주요 변화
    comparison_note = models.TextField(blank=True)  # 과거 기록과의 비교
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.swim_record} - {self.get_analysis_type_display()}"   