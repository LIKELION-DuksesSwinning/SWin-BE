# records/admin.py
from django.contrib import admin
from .models import SwimRecord, SwimRecordSymptom

@admin.register(SwimRecord)
class SwimRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'timing', 'created_at')

@admin.register(SwimRecordSymptom)
class SwimRecordSymptomAdmin(admin.ModelAdmin):
    list_display = ('id', 'swim_record', 'symptom_type', 'score')