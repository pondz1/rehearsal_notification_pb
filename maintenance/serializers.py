from rest_framework import serializers
from .models import *

class MaintenanceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceImage
        fields = '__all__'

class CompletionImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompletionImage
        fields = '__all__'

class MaintenanceRequestSerializer(serializers.ModelSerializer):
    images = MaintenanceImageSerializer(source='maintenanceimage_set', many=True, read_only=True)
    completion_images = CompletionImageSerializer(source='completionimage_set', many=True, read_only=True)
    requestor_name = serializers.CharField(source='requestor.get_full_name', read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id', 'title', 'description', 'category', 'requestor',
            'requestor_name', 'location', 'priority', 'status',
            'created_at', 'updated_at', 'scheduled_date',
            'completion_date', 'images', 'completion_images'
        ]

class MaintenanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceCategory
        fields = '__all__'
