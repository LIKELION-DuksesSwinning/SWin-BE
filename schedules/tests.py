from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from clinic.models import Clinic, ClinicReservation
from records.models import SwimRecord

from .models import Schedule


class SwimScheduleSignalTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="calendar-user",
			password="test-password",
		)
		start = timezone.now()
		self.schedule = Schedule.objects.create(
			user=self.user,
			category="SWIM",
			start_datetime=start,
			end_datetime=start + timedelta(hours=1),
		)

	def test_schedule_is_removed_after_last_swim_record_is_deleted(self):
		record = SwimRecord.objects.create(
			user=self.user,
			schedule=self.schedule,
			timing="AFTER",
		)

		record.delete()

		self.assertFalse(Schedule.objects.filter(pk=self.schedule.pk).exists())

	def test_schedule_remains_until_all_swim_records_are_deleted(self):
		SwimRecord.objects.create(
			user=self.user,
			schedule=self.schedule,
			timing="BEFORE",
		)
		second_record = SwimRecord.objects.create(
			user=self.user,
			schedule=self.schedule,
			timing="AFTER",
		)

		second_record.delete()

		self.assertTrue(Schedule.objects.filter(pk=self.schedule.pk).exists())

	def test_schedule_is_removed_after_admin_style_bulk_delete(self):
		record = SwimRecord.objects.create(
			user=self.user,
			schedule=self.schedule,
			timing="AFTER",
		)

		SwimRecord.objects.filter(pk=record.pk).delete()

		self.assertFalse(Schedule.objects.filter(pk=self.schedule.pk).exists())


class ClinicScheduleSignalTests(TestCase):
	def test_schedule_is_removed_when_reservation_is_deleted(self):
		user = get_user_model().objects.create_user(
			username="clinic-user",
			password="test-password",
		)
		clinic = Clinic.objects.create(
			name="Test Clinic",
			district="Test District",
			phone="010-0000-0000",
		)
		reservation = ClinicReservation.objects.create(
			user=user,
			clinic=clinic,
			status=ClinicReservation.Status.BOOKED,
		)
		schedule = Schedule.objects.create(
			user=user,
			category="CLINIC",
			start_datetime=timezone.now(),
			end_datetime=timezone.now() + timedelta(hours=1),
			clinic_reservation=reservation,
		)

		reservation.delete()

		self.assertFalse(Schedule.objects.filter(pk=schedule.pk).exists())

# Create your tests here.
