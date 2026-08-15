from rest_framework import serializers
from .models import Notification

class NotificationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'category',
            'category_display',
            'title',
            'content',
            'is_read',
            'created_at'
        ]
        read_only_fields = ['id', 'category', 'title', 'content', 'created_at']