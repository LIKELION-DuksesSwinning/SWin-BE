from rest_framework import serializers
from .models import Schedule

class ScheduleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'id', 
            'category', 
            'category_display', 
            'start_datetime', 
            'end_datetime', 
            'memo', 
            'is_repeat', 
            'repeat_option',
            'clinic_reservation'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        # 현재 로그인된 유저를 자동으로 할당
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)