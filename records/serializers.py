import json

from django.db import transaction
from rest_framework import serializers

from accounts.models import NotificationSetting
from notifications.models import Notification

from .models import SwimRecord, SwimRecordSymptom


class SwimRecordSymptomSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="symptom_type")

    class Meta:
        model = SwimRecordSymptom
        fields = ["type", "score"]


class SymptomListField(serializers.Field):
    def to_internal_value(self, data):
        if data in (None, ""):
            return []

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                raise serializers.ValidationError("symptoms must be a valid JSON array.")

        if not isinstance(data, list):
            raise serializers.ValidationError("symptoms must be a list.")

        symptoms = []
        for item in data:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each symptom must be an object.")

            symptom_type = item.get("type") or item.get("symptom_type")
            score = item.get("score")
            if not symptom_type or not score:
                raise serializers.ValidationError("Each symptom requires type and score.")

            symptoms.append({"type": symptom_type, "score": score})

        return symptoms

    def to_representation(self, value):
        return value


def replace_symptoms(swim_record, symptoms):
    swim_record.symptoms.all().delete()
    SwimRecordSymptom.objects.bulk_create([
        SwimRecordSymptom(
            swim_record=swim_record,
            symptom_type=item["type"],
            score=item["score"],
        )
        for item in symptoms
    ])


class SwimRecordNestedSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source="id", read_only=True)
    photo_url = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()

    class Meta:
        model = SwimRecord
        fields = ["record_id", "timing", "photo_url", "swim_time", "symptoms", "memo", "created_at"]

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_symptoms(self, obj):
        return SwimRecordSymptomSerializer(obj.symptoms.all(), many=True).data


class SwimRecordDetailSerializer(serializers.ModelSerializer):
    record_id = serializers.IntegerField(source="id", read_only=True)
    photo_url = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()
    additional_records = serializers.SerializerMethodField()

    class Meta:
        model = SwimRecord
        fields = [
            "record_id",
            "timing",
            "photo",
            "photo_url",
            "swim_time",
            "symptoms",
            "additional_records",
            "memo",
            "created_at",
        ]
        read_only_fields = ["record_id", "timing", "created_at", "photo_url", "additional_records"]
        extra_kwargs = {
            "photo": {"write_only": True, "required": False},
        }

    def get_photo_url(self, obj):
        if not obj.photo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url

    def get_symptoms(self, obj):
        return SwimRecordSymptomSerializer(obj.symptoms.all(), many=True).data

    def get_additional_records(self, obj):
        if obj.timing == "ADD":
            return []
        records = obj.additional_records.order_by("created_at")
        return SwimRecordNestedSerializer(records, many=True, context=self.context).data


class SwimRecordCreateSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    symptoms = SymptomListField(required=False, write_only=True)

    class Meta:
        model = SwimRecord
        fields = ["timing", "schedule", "photo", "swim_time", "memo", "symptoms"]

    def validate_schedule(self, schedule):
        request = self.context.get("request")
        if schedule and request and schedule.user_id != request.user.id:
            raise serializers.ValidationError("Only your own schedule can be linked.")
        return schedule

    @transaction.atomic
    def create(self, validated_data):
        symptoms = validated_data.pop("symptoms", [])
        user = self.context["request"].user
        parent_record = validated_data.get("parent_record")
        if validated_data.get("timing") == "ADD" and parent_record is None:
            raise serializers.ValidationError({"timing": "ADD records must be created from a parent record."})
        if parent_record and not validated_data.get("schedule"):
            validated_data["schedule"] = parent_record.schedule

        swim_record = SwimRecord.objects.create(user=user, **validated_data)

        if symptoms:
            replace_symptoms(swim_record, symptoms)

        notification_setting, _ = NotificationSetting.objects.get_or_create(user=user)
        if notification_setting.swim_after_record_noti:
            timing_display = {
                "BEFORE": "Before swim",
                "AFTER": "After swim",
                "ADD": "Additional",
            }.get(swim_record.timing, "Swim")

            Notification.objects.create(
                user=user,
                category="SWIM_RECORD",
                title=f"{timing_display} skin record saved",
                content=f"{timing_display} skin record was saved successfully.",
            )

        return swim_record


class SwimRecordUpdateSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=False, allow_null=True, allow_empty_file=True)
    symptoms = SymptomListField(required=False, write_only=True)

    class Meta:
        model = SwimRecord
        fields = ["photo", "swim_time", "memo", "symptoms"]

    @transaction.atomic
    def update(self, instance, validated_data):
        symptoms = validated_data.pop("symptoms", None)
        instance = super().update(instance, validated_data)
        if symptoms is not None:
            replace_symptoms(instance, symptoms)
        return instance
