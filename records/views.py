from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from .models import SwimRecord
from .serializers import (
    SwimRecordCreateSerializer,
    SwimRecordDetailSerializer
)

# 1.2.1 / 1.2.2 수영 기록 등록 (POST) 및 홈 화면 목록 조회 (GET)
class SwimRecordListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    # 홈 화면 내 수영 기록 목록 조회 (정렬 지원)
    def get(self, request):
        sort_option = request.query_params.get('sort', 'latest')
        queryset = SwimRecord.objects.filter(user=request.user, timing__in=['BEFORE', 'AFTER'])

        if sort_option == 'oldest':
            queryset = queryset.order_by('created_at')
        else:
            queryset = queryset.order_by('-created_at')

        serializer = SwimRecordDetailSerializer(queryset, many=True, context={'request': request})
        return Response({"records": serializer.data}, status=status.HTTP_200_OK)

    # 1.2.1 / 1.2.2 수영 전/후 기록 등록
    def post(self, request):
        serializer = SwimRecordCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            record = serializer.save()
            return Response({
                "record_id": record.id,
                "message": "저장되었습니다."
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 1.2.4 이전 기록 상세 조회 (GET) 및 수정 (PATCH)
class SwimRecordDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, record_id, user):
        return get_object_or_404(SwimRecord, id=record_id, user=user)

    def get(self, request, record_id):
        record = self.get_object(record_id, request.user)
        serializer = SwimRecordDetailSerializer(record, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, record_id):
        record = self.get_object(record_id, request.user)
        serializer = SwimRecordDetailSerializer(record, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 1.2.3 추가 기록 작성 (POST /api/v1/records/swim/{record_id}/additional/)
class AdditionalSkinRecordCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, record_id):
        parent_record = get_object_or_404(SwimRecord, id=record_id, user=request.user)
        
        # multipart 데이터 복사 및 추가 속성 세팅
        data = request.data.copy()
        data['timing'] = 'ADD'
        
        serializer = SwimRecordCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            additional_record = serializer.save(parent_record=parent_record)
            return Response({
                "additional_record_id": additional_record.id,
                "message": "저장되었습니다."
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)