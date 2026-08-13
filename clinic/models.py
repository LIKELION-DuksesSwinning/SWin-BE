from django.conf import settings
from django.db import models
from records.models import SwimRecord


class Clinic(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class ClinicReferral(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clinic_referrals')
    swim_record = models.ForeignKey(SwimRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='clinic_referrals')
    trigger_reason = models.CharField(max_length=255) 
    user_consented = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.trigger_reason}"


class ClinicReservation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '예약 대기'
        CONFIRMED = 'confirmed', '예약 확정'
        CANCELLED = 'cancelled', '취소'
        COMPLETED = 'completed', '방문 완료'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='clinic_reservations')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='reservations')
    visit_date = models.DateField()
    visit_time = models.TimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"{self.user} - {self.clinic} - {self.visit_date}"