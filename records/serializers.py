import json
from rest_framework import serializers
from .models import SwimRecord, SwimRecordSymptom
from notifications.models import Notification  # [추가] 알림 모델 임포트


class SwimRecordSymptomSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='symptom_type')

    class Meta:
        model = SwimRecordSymptom
        fields = ['type', 'score']


# 1.2.4 이전 기록 상세 조회 & 수정용 Serializer
class SwimRecordDetailSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='id', read_only=True)
    photo_url = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()

    class Meta:
        model = SwimRecord
        fields = [
            'record_id',
            'timing',
            'photo',
            'photo_url',
            'swim_time',
            'symptoms',
            'memo',
            'created_at'
        ]
        read_only_fields = ['record_id', 'timing', 'created_at', 'photo_url']
        extra_kwargs = {
            'photo': {'write_only': True, 'required': False}
        }

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None

    def get_symptoms(self, obj):
        return SwimRecordSymptomSerializer(obj.symptoms.all(), many=True).data

    def update(self, instance, validated_data):
        request = self.context.get('request')
        symptoms_data = request.data.get('symptoms') if request else None

        instance = super().update(instance, validated_data)

        if symptoms_data is not None:
            if isinstance(symptoms_data, str):
                try:
                    symptoms_list = json.loads(symptoms_data)
                except json.JSONDecodeError:
                    symptoms_list = []
            else:
                symptoms_list = symptoms_data

            instance.symptoms.all().delete()
            symptom_instances = [
                SwimRecordSymptom(
                    swim_record=instance,
                    symptom_type=item.get('type'),
                    score=item.get('score')
                )
                for item in symptoms_list if item.get('type') and item.get('score')
            ]
            if symptom_instances:
                SwimRecordSymptom.objects.bulk_create(symptom_instances)

        return instance


# 1.2.1 / 1.2.2 수영 기록 등록 Serializer
class SwimRecordCreateSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    symptoms = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = SwimRecord
        fields = [
            'timing',
            'schedule',
            'photo',
            'swim_time',
            'memo',
            'symptoms'
        ]

    def create(self, validated_data):
        symptoms_data = validated_data.pop('symptoms', None)
        user = self.context['request'].user
        swim_record = SwimRecord.objects.create(user=user, **validated_data)

        # 1. 증상 데이터 저장
        if symptoms_data:
            if isinstance(symptoms_data, str):
                try:
                    symptoms_list = json.loads(symptoms_data)
                except json.JSONDecodeError:
                    symptoms_list = []
            else:
                symptoms_list = symptoms_data

            symptom_instances = [
                SwimRecordSymptom(
                    swim_record=swim_record,
                    symptom_type=item.get('type'),
                    score=item.get('score')
                )
                for item in symptoms_list if item.get('type') and item.get('score')
            ]
            if symptom_instances:
                SwimRecordSymptom.objects.bulk_create(symptom_instances)

        # 2. [추가] 기록 생성 시 알림(Notification) 자동 생성
        timing_display = {
            'BEFORE': '수영 전',
            'AFTER': '수영 후',
            'ADD': '추가'
        }.get(swim_record.timing, '수영')

        Notification.objects.create(
            user=user,
            category='SWIM_RECORD',
            title=f"{timing_display} 피부 상태 기록 완료",
            content=f"{timing_display} 피부 상태 및 기록이 정상적으로 저장되었습니다."
        )

        return swim_record