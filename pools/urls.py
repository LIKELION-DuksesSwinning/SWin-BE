from django.urls import path

from .views import (
    PoolDetailView,
    PoolListView,
    RegionCityListView,
    RegionDistrictListView,
    RegionDongListView,
)

urlpatterns = [
    path("regions/cities/", RegionCityListView.as_view(), name="pool-region-cities"),
    path("regions/districts/", RegionDistrictListView.as_view(), name="pool-region-districts"),
    path("regions/dongs/", RegionDongListView.as_view(), name="pool-region-dongs"),
    path("", PoolListView.as_view(), name="pool-list"),
    path("<int:pk>/", PoolDetailView.as_view(), name="pool-detail"),
]