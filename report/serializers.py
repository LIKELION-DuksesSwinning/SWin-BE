from rest_framework import serializers
from .models import RoutineRecommendation, WeeklyReport


class RoutineRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutineRecommendation
        fields = ["id", "recommended_swim_count", "recommended_swim_minutes", "skin_care_routine"]


class WeeklyReportSerializer(serializers.ModelSerializer):
    routine = serializers.SerializerMethodField()

    class Meta:
        model = WeeklyReport
        fields = [
            "id", "week_start", "week_end", "swim_count", "avg_swim_duration",
            "symptom_trend", "recommended_ingredients", "recommended_products",
            "clinic_recommended", "other_pool_recommended", "routine", "generated_at",
        ]

    def get_routine(self, obj):
        routine = getattr(obj, "routine", None)
        return RoutineRecommendationSerializer(routine).data if routine else None


class WeeklyReportListSerializer(serializers.ModelSerializer):
    """목록용"""

    class Meta:
        model = WeeklyReport
        fields = ["id", "week_start", "week_end", "clinic_recommended"]


