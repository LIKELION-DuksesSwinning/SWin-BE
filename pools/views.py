from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Pool, Region
from .serializers import PoolSerializer, RegionSerializer


class RegionCityListView(generics.ListAPIView):
    """GET /api/v1/pools/regions/cities/ — 화면1: 시/도 목록"""

    permission_classes = [IsAuthenticated]
    serializer_class = RegionSerializer

    def get_queryset(self):
        return Region.objects.filter(level=Region.Level.SIDO)


class RegionDistrictListView(generics.ListAPIView):
    """GET /api/v1/pools/regions/districts/?city={id} — 화면2: 시/군구 목록"""

    permission_classes = [IsAuthenticated]
    serializer_class = RegionSerializer

    def get_queryset(self):
        city_id = self.request.query_params.get("city")
        qs = Region.objects.filter(level=Region.Level.SIGUNGU)
        if city_id:
            qs = qs.filter(parent_id=city_id)
        return qs


class RegionDongListView(generics.ListAPIView):
    """GET /api/v1/pools/regions/dongs/?district={id} — 화면3: 읍/면/동 목록"""

    permission_classes = [IsAuthenticated]
    serializer_class = RegionSerializer

    def get_queryset(self):
        district_id = self.request.query_params.get("district")
        qs = Region.objects.filter(level=Region.Level.DONG)
        if district_id:
            qs = qs.filter(parent_id=district_id)
        return qs


class PoolListView(generics.ListAPIView):
    """GET /api/v1/pools/?dong={id} — 화면4: 동 선택 시 수영장 목록"""

    permission_classes = [IsAuthenticated]
    serializer_class = PoolSerializer

    def get_queryset(self):
        qs = Pool.objects.all()
        dong_id = self.request.query_params.get("dong")
        if dong_id:
            qs = qs.filter(dong_id=dong_id)
        return qs


class PoolDetailView(generics.RetrieveAPIView):
    """GET /api/v1/pools/{poolId}/ — 수영장 상세"""

    permission_classes = [IsAuthenticated]
    serializer_class = PoolSerializer
    queryset = Pool.objects.all()