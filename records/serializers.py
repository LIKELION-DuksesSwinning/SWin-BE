from rest_framework import serializers
from .models import SwimRecord, SkinRecord
from pools.models import Pool

# 피부 기록(SkinRecord) 시리얼라이저
class SkinRecordSerializer(serializers.ModelSerializer):
    timing_display = serializers.CharField(source='get_timing_display', read_only=True)
    symptom_type_display = serializers.CharField(source='get_symptom_type_display', read_only=True)

    class Meta:
        model = SkinRecord
        fields = [
            'id',
            'timing',
            'timing_display',
            'symptom_type',
            'symptom_type_display',
            'symptom_level',
            'memo',
            'photo'
        ]
        read_only_fields = ['id']


# 수영 기록 상세 조회 & 수정용 시리얼라이저
class SwimRecordDetailSerializer(serializers.ModelSerializer):
    skin_records = SkinRecordSerializer(many=True, read_only=True)
    pool_name = serializers.CharField(source='pool.name', read_only=True)

    class Meta:
        model = SwimRecord
        fields = [
            'id',
            'pool',
            'pool_name',
            'date',
            'start_time',
            'duration_minutes',
            'skin_records'
        ]
        read_only_fields = ['id', 'skin_records']


# 수영 기록 생성 시 수영 정보와 피부 상태를 함께 받기 위한 시리얼라이저
class SwimRecordCreateSerializer(serializers.ModelSerializer):
    skin_record = SkinRecordSerializer(write_only=True, required=False)

    class Meta:
        model = SwimRecord
        fields = [
            'id',
            'pool',
            'date',
            'start_time',
            'duration_minutes',
            'skin_record'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        skin_data = validated_data.pop('skin_record', None)
        user = self.context['request'].user
        swim_record = SwimRecord.objects.create(user=user, **validated_data)

        if skin_data:
            SkinRecord.objects.create(swim_record=swim_record, **skin_data)

        return swim_record