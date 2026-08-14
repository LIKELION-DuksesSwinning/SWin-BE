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
class OnboardingSerializer(serializers.Serializer):
    weekly_swim_count = serializers.IntegerField(required=True, min_value=0)
    avg_swim_time = serializers.IntegerField(required=True, min_value=1)
    swim_period = serializers.CharField(required=True)
    skin_type = serializers.CharField(required=True)
    symptoms = serializers.ListField(
        child=serializers.CharField(), required=True, allow_empty=False
    )
    symptom_areas = serializers.ListField(
        child=serializers.CharField(), required=True, allow_empty=False
    )
    region = serializers.CharField(required=True)

    def create(self, validated_data):
        user = self.context['request'].user
        
        # 1. User 지역(region) 업데이트
        user.region = validated_data['region']
        user.save()

        # 2. UserSkinProfile 생성 (이미 존재하면 update)
        profile, created = UserSkinProfile.objects.update_or_create(
            user=user,
            defaults={
                'weekly_swim_count': validated_data['weekly_swim_count'],
                'avg_swim_time': validated_data['avg_swim_time'],
                'swim_period': validated_data['swim_period'],
                'skin_type': validated_data['skin_type'],
            }
        )

        # 3. 기존 증상/부위 데이터 초기화 후 재생성
        UserSkinSymptom.objects.filter(profile=profile).delete()
        UserSkinArea.objects.filter(profile=profile).delete()

        symptoms_objs = [
            UserSkinSymptom(profile=profile, symptom=symptom)
            for symptom in validated_data['symptoms']
        ]
        UserSkinSymptom.objects.bulk_create(symptoms_objs)

        areas_objs = [
            UserSkinArea(profile=profile, area=area)
            for area in validated_data['symptom_areas']
        ]
        UserSkinArea.objects.bulk_create(areas_objs)

        return profile
    
    
# ==========================================   
# 5.1.1 약관 및 정책 Serializer 추가
 
    
    # 약관 조회용 Serializer
class AgreementSerializer(serializers.ModelSerializer):
    terms_type_display = serializers.CharField(source='get_terms_type_display', read_only=True)

    class Meta:
        model = Agreement
        fields = ['terms_type', 'terms_type_display', 'is_agreed', 'agreed_at']

# 약관 일괄 업데이트(POST)용 Serializer
class AgreementUpdateItemSerializer(serializers.Serializer):
    terms_type = serializers.ChoiceField(choices=Agreement.TERMS_CHOICES)
    is_agreed = serializers.BooleanField()

class AgreementBulkUpdateSerializer(serializers.Serializer):
    agreements = serializers.ListField(
        child=AgreementUpdateItemSerializer(),
        allow_empty=False
    )
    
    
    
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