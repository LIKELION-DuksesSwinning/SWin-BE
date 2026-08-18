from rest_framework import serializers

from .models import Analysis


class AnalysisCreateSerializer(serializers.Serializer):
    """POST /api/v1/analysis/ 요청 바디"""

    swim_record_id = serializers.IntegerField()

    def validate_swim_record_id(self, value):
        from .models import SwimRecord

        request = self.context["request"]
        try:
            swim_record = SwimRecord.objects.get(id=value, user=request.user)
        except SwimRecord.DoesNotExist:
            raise serializers.ValidationError("본인 소유의 수영 기록이 아니거나 존재하지 않습니다.")

        has_before = swim_record.skin_records.filter(timing="before").exists()
        has_after = swim_record.skin_records.filter(timing="after").exists()
        if not (has_before and has_after):
            raise serializers.ValidationError(
                "분석하려면 수영 전/후 기록이 모두 필요합니다.", code="insufficient_data"
            )

        self.context["swim_record"] = swim_record
        return value


class AnalysisListSerializer(serializers.ModelSerializer):
    """분석 이력 목록용 (가벼운 버전)"""

    class Meta:
        model = Analysis
        fields = ["id", "pattern_types", "created_at"]


class AnalysisDetailSerializer(serializers.ModelSerializer):
    """분석 결과 상세/생성 응답용"""

    clinic_recommendation = serializers.SerializerMethodField()

    class Meta:
        model = Analysis
        fields = [
            "id", "pattern_types", "pattern_description", "symptom_changes",
            "four_week_trend", "clinic_recommendation", "disclaimer", "created_at",
        ]

    def get_clinic_recommendation(self, obj):
        if not obj.clinic_recommended:
            return {"shown": False, "text": None, "ctaLabel": None}

        text_map = {
            "score_streak": "최근 증상 점수가 계속 상승하고 있어요. 정확한 피부 분석을 위해 더나 클리닉 상담을 추천드려요.",
            "persisted_72h": "증상이 72시간 이상 지속되고 있어요. 정확한 피부 분석을 위해 더나 클리닉 상담을 추천드려요.",
            "recurring_2w": "최근 2주간 피부 상태가 반복적으로 악화되었어요. 정확한 피부 분석을 위해 더나 클리닉 상담을 추천드려요.",
            "photo_diff_severe": "수영 전후 피부 변화가 뚜렷하게 관찰됐어요. 정확한 피부 분석을 위해 더나 클리닉 상담을 추천드려요.",
        }
        return {
            "shown": True,
            "text": text_map.get(obj.clinic_trigger_reason, ""),
            "ctaLabel": "더나 클리닉 예약 바로가기",
        }