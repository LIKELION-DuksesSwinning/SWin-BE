import uuid
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from rest_framework import serializers
from .models import Schedule

# 조회 및 수정용 Serializer
class ScheduleSerializer(serializers.ModelSerializer):
    schedule_id = serializers.IntegerField(source='id', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'schedule_id',
            'category',
            'category_display',
            'start_datetime',
            'end_datetime',
            'memo',
            'is_repeat',
            'repeat_interval_weeks',
            'repeat_end_type',
            'repeat_count',
            'repeat_until',
            'clinic_reservation'
        ]
        read_only_fields = ['schedule_id', 'category_display']


# 일정 등록 전용 Serializer (반복 bulk_create 지원)
class ScheduleCreateSerializer(serializers.ModelSerializer):
    repeat_interval_weeks = serializers.IntegerField(default=1, required=False, allow_null=True)
    repeat_end_type = serializers.ChoiceField(choices=Schedule.REPEAT_END_CHOICES, required=False, allow_null=True)
    repeat_count = serializers.IntegerField(required=False, allow_null=True)
    repeat_until = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = Schedule
        fields = [
            'category',
            'start_datetime',
            'end_datetime',
            'memo',
            'is_repeat',
            'repeat_interval_weeks',
            'repeat_end_type',
            'repeat_count',
            'repeat_until',
            'clinic_reservation'
        ]

    def validate(self, data):
        if data.get('start_datetime') >= data.get('end_datetime'):
            raise serializers.ValidationError("종료 일시는 시작 일시 이후여야 합니다.")

        if data.get('is_repeat'):
            end_type = data.get('repeat_end_type')
            if not end_type:
                raise serializers.ValidationError({"repeat_end_type": "반복 종료 조건을 선택해주세요."})
            if end_type == 'COUNT' and not data.get('repeat_count'):
                raise serializers.ValidationError({"repeat_count": "반복 횟수를 입력해주세요."})
            if end_type == 'UNTIL_DATE' and not data.get('repeat_until'):
                raise serializers.ValidationError({"repeat_until": "반복 종료 날짜를 지정해주세요."})
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        is_repeat = validated_data.get('is_repeat', False)

        # 1. 단일 일정 등록
        if not is_repeat:
            return Schedule.objects.create(user=user, **validated_data)

        # 2. 반복 일정 등록 (bulk_create 계산)
        interval_weeks = validated_data.get('repeat_interval_weeks') or 1
        end_type = validated_data.get('repeat_end_type')
        repeat_count = validated_data.get('repeat_count')
        repeat_until = validated_data.get('repeat_until')

        group_id = uuid.uuid4()
        schedules_to_create = []

        curr_start = validated_data['start_datetime']
        curr_end = validated_data['end_datetime']
        duration = curr_end - curr_start

        # '계속 반복(FOREVER)' 선택 시 최대 6개월치 사전 생성
        max_limit_date = curr_start.date() + relativedelta(months=6)

        count = 0
        while True:
            # 반복 종료 조건 검증
            if end_type == 'COUNT' and count >= repeat_count:
                break
            if end_type == 'UNTIL_DATE' and curr_start.date() > repeat_until:
                break
            if end_type == 'FOREVER' and curr_start.date() > max_limit_date:
                break

            schedules_to_create.append(
                Schedule(
                    user=user,
                    category=validated_data['category'],
                    start_datetime=curr_start,
                    end_datetime=curr_start + duration,
                    memo=validated_data.get('memo'),
                    is_repeat=True,
                    repeat_group_id=group_id,
                    repeat_interval_weeks=interval_weeks,
                    repeat_end_type=end_type,
                    repeat_count=repeat_count,
                    repeat_until=repeat_until,
                    clinic_reservation=validated_data.get('clinic_reservation')
                )
            )

            count += 1
            curr_start += timedelta(weeks=interval_weeks)

        created_schedules = Schedule.objects.bulk_create(schedules_to_create)
        return created_schedules[0] if created_schedules else None