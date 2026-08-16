import json
from rest_framework import serializers
from .models import SwimRecord, SwimRecordSymptom

class SwimRecordSymptomSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source='symptom_type')

    class Meta:
        model = SwimRecordSymptom
        fields = ['type', 'score']


# 1.2.4 이전 기록 상세 조회용
class SwimRecordDetailSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source='id', read_only=True)
    photo_url = serializers.SerializerMethodField()
    symptoms = SwimRecordSymptomSerializer(many=True, read_only=True)

    class Meta:
        model = SwimRecord
        fields = [
            'record_id',
            'timing',
            'photo_url',
            'swim_time',
            'symptoms',
            'memo',
            'created_at'
        ]

    def get_photo_url(self, obj):
        if obj.photo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None


# 1.2.1 / 1.2.2 수영 기록 등록 Serializer (Multipart 지원)
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

        # symptoms 파싱 및 저장 (JSON String 또는 List)
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