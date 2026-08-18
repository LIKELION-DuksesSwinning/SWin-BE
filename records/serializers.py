import json
from rest_framework import serializers
from .models import SwimRecord, SwimRecordSymptom

class SwimRecordSymptomSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='symptom_type')

    class Meta:
        model = SwimRecordSymptom
        fields = ['type', 'score']


# 1.2.4 이전 기록 상세 조회 & 수정용 Serializer
class SwimRecordDetailSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='id', read_only=True)
    photo_url = serializers.SerializerMethodField()
    # 조회 시에는 객체 리스트 반환
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

    # PATCH 수정 시 증상(symptoms) 갱신 로직
    def update(self, instance, validated_data):
        request = self.context.get('request')
        symptoms_data = request.data.get('symptoms') if request else None

        # 기본 필드 (swim_time, memo, photo 등) 수정
        instance = super().update(instance, validated_data)

        # symptoms 데이터가 들어온 경우 기존 증상 삭제 후 새로 등록
        if symptoms_data is not None:
            if isinstance(symptoms_data, str):
                try:
                    symptoms_list = json.loads(symptoms_data)
                except json.JSONDecodeError:
                    symptoms_list = []
            else:
                symptoms_list = symptoms_data

            # 기존 증상 데이터 교체
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

        return swim_record