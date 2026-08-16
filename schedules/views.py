from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Schedule
from .serializers import ScheduleSerializer

# 1.1.1 캘린더 월별 조회 & 1.1.2 일정 등록
class ScheduleListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    # 1.1.1 캘린더 일정 조회 (GET /api/v1/schedules/?year=2026&month=8)
    def get(self, request):
        user = request.user
        queryset = Schedule.objects.filter(user=user)

        year = request.query_params.get('year')
        month = request.query_params.get('month')

        # 쿼리 파라미터가 들어온 경우 해당 연도/월로 필터링
        if year and month:
            queryset = queryset.filter(
                start_datetime__year=year,
                start_datetime__month=month
            )

        queryset = queryset.order_by('start_datetime')
        serializer = ScheduleSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 1.1.2 일정 직접 등록 (POST /api/v1/schedules/)
    def post(self, request):
        serializer = ScheduleSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 1.1.2 일정 수정(PATCH) 및 삭제(DELETE) (/api/v1/schedules/{schedule_id}/)
class ScheduleDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, schedule_id, user):
        return get_object_or_404(Schedule, id=schedule_id, user=user)

    # 일정 수정
    def patch(self, request, schedule_id):
        schedule = self.get_object(schedule_id, request.user)
        serializer = ScheduleSerializer(schedule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 일정 삭제
    def delete(self, request, schedule_id):
        schedule = self.get_object(schedule_id, request.user)
        schedule.delete()
        return Response({"detail": "일정이 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)