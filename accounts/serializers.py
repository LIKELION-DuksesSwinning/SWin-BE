from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import *

# 0.1 로그인 Serializer
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("아이디 또는 비밀번호가 불일치합니다.")

        # JWT 토큰 생성
        refresh = RefreshToken.for_user(user)
        return {
            'token': str(refresh.access_token),
            'user_id': user.id,
            'name': user.name or user.username
        }

# 0.2 온보딩 Serializer
# 선택 옵션 유효성 검증용 리스트
VALID_PERIODS = ["6개월 미만", "6개월~1년", "1~2년", "2~4년", "4년 이상"]
VALID_SWIM_COUNTS = ["주 1~2회", "주 3~4회", "주 5회 이상"]
VALID_SWIM_TIMES = ["30분 미만", "30~60분", "60~90분", "90분 이상"]
VALID_SKIN_TYPES = ["건성", "지성", "복합성", "수부지", "민감성"]
VALID_SYMPTOMS = ["당김", "건조", "가려움", "붉음", "여드름", "없음"]
VALID_AREAS = ["이마", "왼쪽 볼", "오른쪽 볼", "나비존", "하관", "전체"]

class OnboardingSerializer(serializers.Serializer):
    swim_period = serializers.ChoiceField(choices=VALID_PERIODS)
    weekly_swim_count = serializers.ChoiceField(choices=VALID_SWIM_COUNTS)
    avg_swim_time = serializers.ChoiceField(choices=VALID_SWIM_TIMES)
    skin_types = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_SKIN_TYPES),
        allow_empty=False
    )
    symptoms = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_SYMPTOMS),
        allow_empty=False
    )
    symptom_areas = serializers.ListField(
        child=serializers.ChoiceField(choices=VALID_AREAS),
        required=False,
        default=list
    )

    def create(self, validated_data):
        user = self.context['request'].user

        # 1. UserSkinProfile 생성 (이미 존재하면 update)
        profile, _ = UserSkinProfile.objects.update_or_create(
            user=user,
            defaults={
                'weekly_swim_count': validated_data['weekly_swim_count'],
                'avg_swim_time': validated_data['avg_swim_time'],
                'swim_period': validated_data['swim_period'],
            }
        )

        # 2. 다중 선택 항목들 기존 데이터 삭제 후 일괄 생성
        UserSkinType.objects.filter(profile=profile).delete()
        UserSkinSymptom.objects.filter(profile=profile).delete()
        UserSkinArea.objects.filter(profile=profile).delete()

        # 피부 타입 일괄 생성
        skin_type_objs = [
            UserSkinType(profile=profile, skin_type=skin_type)
            for skin_type in validated_data['skin_types']
        ]
        UserSkinType.objects.bulk_create(skin_type_objs)

        # 증상 일괄 생성
        symptom_objs = [
            UserSkinSymptom(profile=profile, symptom=symptom)
            for symptom in validated_data['symptoms']
        ]
        UserSkinSymptom.objects.bulk_create(symptom_objs)

        # 부위 일괄 생성 (선택된 경우만)
        if validated_data.get('symptom_areas'):
            area_objs = [
                UserSkinArea(profile=profile, area=area)
                for area in validated_data['symptom_areas']
            ]
            UserSkinArea.objects.bulk_create(area_objs)

        return profile
    
    
# ==========================================   
# 5.1.1 약관 및 정책 Serializer 추가
 
    
# 5.1.1 약관 및 정책
class AgreementSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='get_terms_type_display', read_only=True)

    class Meta:
        model = Agreement
        fields = ['terms_type', 'title', 'is_agreed', 'agreed_at']

class AgreementUpdateSerializer(serializers.Serializer):
    terms_type = serializers.ChoiceField(choices=Agreement.TERMS_CHOICES)
    is_agreed = serializers.BooleanField()

# 5.1.2 푸시 알림 설정
class NotificationSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationSetting
        fields = [
            'swim_after_record_noti', 
            'clinic_reservation_noti', 
            'swim_schedule_noti', 
            'weekly_report_noti'
        ]

# 5.1.3 프로필 설정
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'birth_date', 'gender']

# 5.1.4 로그아웃
class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)