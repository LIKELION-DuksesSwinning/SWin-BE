from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .serializers import LoginSerializer, OnboardingSerializer

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