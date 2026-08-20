from django.contrib import admin

from .models import Schedule


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
	list_display = (
		"id",
		"user",
		"category",
		"start_datetime",
		"end_datetime",
		"clinic_reservation",
	)
	list_filter = ("category", "is_repeat")
	search_fields = ("user__username", "user__email", "memo")
	date_hierarchy = "start_datetime"
