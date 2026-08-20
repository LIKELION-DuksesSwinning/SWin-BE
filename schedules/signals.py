from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from clinic.models import ClinicReservation
from records.models import SwimRecord

from .models import Schedule


@receiver(pre_delete, sender=ClinicReservation)
def delete_clinic_schedule_with_reservation(sender, instance, **kwargs):
    Schedule.objects.filter(clinic_reservation=instance).delete()


@receiver(post_delete, sender=SwimRecord)
def delete_empty_swim_schedule_after_record_delete(sender, instance, **kwargs):
    schedule_id = getattr(instance, "_schedule_id_before_delete", None)
    if not schedule_id:
        return

    schedule = Schedule.objects.filter(id=schedule_id, category="SWIM").first()
    if schedule and not schedule.swim_records.exists():
        schedule.delete()


@receiver(pre_delete, sender=SwimRecord)
def remember_swim_schedule_before_record_delete(sender, instance, **kwargs):
    instance._schedule_id_before_delete = instance.schedule_id
