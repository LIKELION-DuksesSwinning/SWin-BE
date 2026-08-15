from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import SwimRecord, SkinRecord
from .serializers import (
    SwimRecordCreateSerializer,
    SwimRecordDetailSerializer,
    SkinRecordSerializer
)

# 1.2.1 / 1.2.2 수영 기록 등록 (POST) 및 목록 조회 (GET)
class SwimRecordListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        records = SwimRecord.objects.filter(user=request.user)
        serializer = SwimRecordDetailSerializer(records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = SwimRecordCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            record = serializer.save()
            return Response(
                SwimRecordDetailSerializer(record).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 1.2.4 수영 기록 상세 조회 (GET) 및 수정 (PATCH)
class SwimRecordDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, record_id, user):
        return get_object_or_404(SwimRecord, id=record_id, user=user)

    def get(self, request, record_id):
        record = self.get_object(record_id, request.user)
        serializer = SwimRecordDetailSerializer(record)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, record_id):
        record = self.get_object(record_id, request.user)
        serializer = SwimRecordDetailSerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 1.2.3 추가 기록 작성 (POST /api/v1/records/swim/{record_id}/additional/)
class AdditionalSkinRecordCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, record_id):
        swim_record = get_object_or_404(SwimRecord, id=record_id, user=request.user)
        serializer = SkinRecordSerializer(data=request.data)
        if serializer.is_valid():
            # timing을 additional로 고정하여 생성
            serializer.save(swim_record=swim_record, timing=SkinRecord.Timing.ADDITIONAL)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)