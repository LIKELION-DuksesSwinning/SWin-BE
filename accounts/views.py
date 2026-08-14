from django.utils import timezone
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
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
                    "profile_id": profile.id,
                    "user_id": request.user.id,
                    "message": "온보딩 정보가 성공적으로 저장되었습니다."
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {"detail": "필수 항목을 모두 입력해야 합니다."},
            status=status.HTTP_400_BAD_REQUEST
        )


# ==========================================
# 5.1.1 약관 및 정책 API

class AgreementView(APIView):
    permission_classes = [IsAuthenticated]

    # 약관 동의 목록 조회 (GET)
    def get(self, request):
        user = request.user
        
        # 유저에게 아직 생성되지 않은 약관이 있다면 기본값(False)으로 초기 레코드 생성
        for term_code, _ in Agreement.TERMS_CHOICES:
            Agreement.objects.get_or_create(user=user, terms_type=term_code)
            
        agreements = user.agreements.all().order_by('id')
        serializer = AgreementSerializer(agreements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 약관 동의 상태 업데이트 (POST)
    def post(self, request):
        serializer = AgreementBulkUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        items = serializer.validated_data['agreements']

        for item in items:
            terms_type = item['terms_type']
            is_agreed = item['is_agreed']
            
            agreement, _ = Agreement.objects.get_or_create(user=user, terms_type=terms_type)
            agreement.is_agreed = is_agreed
            agreement.agreed_at = timezone.now() if is_agreed else None
            agreement.save()

        updated_agreements = user.agreements.all().order_by('id')
        return Response(
            AgreementSerializer(updated_agreements, many=True).data,
            status=status.HTTP_200_OK
        )
        
        
# 5.1.2 푸시 알림
class NotificationSettingView(APIView):
    permission_classes = [IsAuthenticated]

    # 5.1.2 알림 설정 조회 (GET)
    def get(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        serializer = NotificationSettingSerializer(setting)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 5.1.2 알림 설정 변경 (PATCH)
    def patch(self, request):
        setting, _ = NotificationSetting.objects.get_or_create(user=request.user)
        serializer = NotificationSettingSerializer(setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "알림 설정이 변경되었습니다.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
# 5.1.3 프로필 설정
class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    # 5.1.3 프로필 정보 조회 (GET)
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 5.1.3 프로필 정보 수정 (PATCH)
    def patch(self, request):
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "프로필 정보가 성공적으로 수정되었습니다.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)