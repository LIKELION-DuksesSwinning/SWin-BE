from django.contrib import admin

from .models import Clinic, ClinicReservation


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "district", "phone"]
    search_fields = ["name", "district"]


@admin.register(ClinicReservation)
class ClinicReservationAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "clinic", "visit_date", "visit_time", "status", "created_at"]
    list_filter = ["status", "clinic"]
    search_fields = ["user__username", "clinic__name"]
    autocomplete_fields = ["clinic"]
    readonly_fields = ["created_at", "updated_at"]
