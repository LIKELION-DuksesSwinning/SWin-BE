from rest_framework import serializers

from .models import Pool, Region


class RegionSerializer(serializers.ModelSerializer):
    """3.1 시/도, 시/군구, 읍/면/동 목록 공용"""

    class Meta:
        model = Region
        fields = ["id", "name"]


class PoolSerializer(serializers.ModelSerializer):
    """3.1 동 선택 시 수영장 목록, 수영장 상세 공용"""

    class Meta:
        model = Pool
        fields = ["id", "name", "address", "phone"]