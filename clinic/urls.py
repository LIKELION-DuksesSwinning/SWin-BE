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
    path("clinics/", ClinicListView.as_view(), name="clinic-list"),
    path("clinics/<int:clinic_id>/available-times/", ClinicAvailableTimesView.as_view(), name="clinic-available-times"),
    path("clinics/referrals/", ClinicReferralListView.as_view(), name="clinic-referral-list"),
    path("clinics/referrals/<int:referral_id>/consent/", ClinicReferralConsentView.as_view(), name="clinic-referral-consent"),
    path("clinics/reservations/", ClinicReservationListCreateView.as_view(), name="clinic-reservation-list-create"),
    path("clinics/reservations/<int:pk>/", ClinicReservationDetailUpdateView.as_view(), name="clinic-reservation-detail"),
]
