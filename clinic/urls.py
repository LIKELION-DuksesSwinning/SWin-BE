from django.urls import path

from .views import (
    ClinicAvailableTimesView,
    ClinicListView,
    ClinicReferralConsentView,
    ClinicReferralListView,
    ClinicReservationDetailUpdateView,
    ClinicReservationListCreateView,
)

urlpatterns = [
    path("", ClinicListView.as_view(), name="clinic-list"),
    path("<int:clinic_id>/available-times/", ClinicAvailableTimesView.as_view(), name="clinic-available-times"),
    path("referrals/", ClinicReferralListView.as_view(), name="clinic-referral-list"),
    path("referrals/<int:referral_id>/consent/", ClinicReferralConsentView.as_view(), name="clinic-referral-consent"),
    path("reservations/", ClinicReservationListCreateView.as_view(), name="clinic-reservation-list-create"),
    path("reservations/<int:pk>/", ClinicReservationDetailUpdateView.as_view(), name="clinic-reservation-detail"),
]
