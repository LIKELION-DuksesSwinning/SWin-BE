from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import *
from .models import *

# 0.1 로그인 API
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(serializer.validated_data, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "아이디 또는 비밀번호가 불일치합니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

# 0.2 온보딩 API
class OnboardingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OnboardingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            profile = serializer.save()
            
            return Response(
                {
                    "message": "사용자 피부 및 수영 기록이 성공적으로 저장되었습니다.",
                    "data": {
                        "swim_period": profile.swim_period,
                        "weekly_swim_count": profile.weekly_swim_count,
                        "avg_swim_time": profile.avg_swim_time,
                        "skin_types": list(profile.skin_types.values_list('skin_type', flat=True)),
                        "symptoms": list(profile.symptoms.values_list('symptom', flat=True)),
                        "symptom_areas": list(profile.areas.values_list('area', flat=True)),
                    }
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 5.1.1 약관 및 정책 API
class AgreementView(APIView):
    permission_classes = [IsAuthenticated]

    # 약관 동의 목록 조회 (GET)
    def get(self, request):
        user = request.user
        
        for term_code, _ in Agreement.TERMS_CHOICES:
            Agreement.objects.get_or_create(user=user, terms_type=term_code)
            
        agreements = user.agreements.all().order_by('id')
        serializer = AgreementSerializer(agreements, many=True)
        # [수정] {"agreements": [...]} 구조로 감싸서 반환
        return Response({"agreements": serializer.data}, status=status.HTTP_200_OK)

    # 약관 동의 상태 업데이트 (POST)
    def post(self, request):
        # [수정] 단일 항목 업데이트 시리얼라이저 사용
        serializer = AgreementUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        terms_type = serializer.validated_data['terms_type']
        is_agreed = serializer.validated_data['is_agreed']
        
        agreement, _ = Agreement.objects.get_or_create(user=request.user, terms_type=terms_type)
        agreement.is_agreed = is_agreed
        agreement.agreed_at = timezone.now() if is_agreed else None
        agreement.save()

        # [수정] 명세서 POST Response 포맷 적용
        return Response({
            "terms_type": agreement.terms_type,
            "is_agreed": agreement.is_agreed,
            "message": "약관 동의 상태가 변경되었습니다."
        }, status=status.HTTP_200_OK)


# 5.1.2 푸시 알림
class NotificationSettingView(APIView):
    permission_classes = [IsAuthenticated]

    # 알림 설정 조회 (GET)
    def get(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        serializer = NotificationSettingSerializer(setting)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 알림 설정 변경 (PATCH)
    def patch(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        serializer = NotificationSettingSerializer(setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "알림 설정이 수정되었습니다."
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 5.1.3 프로필 설정
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # 프로필 정보 조회 (GET)
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 프로필 정보 수정 (PATCH)
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # [수정] 명세서에 맞게 data 객체 없이 flat 구조로 message 병합
            response_data = serializer.data
            response_data["message"] = "프로필 정보가 수정되었습니다."
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 5.1.4 로그아웃
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # [수정] 필드명을 refresh_token으로 조회
            refresh_token = serializer.validated_data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            # [수정] 명세서 메시지와 통일
            return Response(
                {"message": "로그아웃 되었습니다."}, 
                status=status.HTTP_200_OK
            )
        except TokenError:
            return Response(
                {"detail": "유효하지 않거나 이미 만료된 토큰입니다."}, 
                status=status.HTTP_400_BAD_REQUEST
            )