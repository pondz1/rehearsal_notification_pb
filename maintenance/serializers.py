from rest_framework import serializers
from .models import *

class MaintenanceImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceImage
        fields = '__all__'

class MaintenanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceCategory
        fields = '__all__'


class EvaluationImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvaluationImage
        fields = ['id', 'image', 'caption', 'uploaded_at']


class RepairEvaluationSerializer(serializers.ModelSerializer):
    images = EvaluationImageSerializer(many=True, read_only=True)
    technician_name = serializers.SerializerMethodField()

    class Meta:
        model = RepairEvaluation
        fields = ['id', 'maintenance_request', 'technician', 'technician_name', 'result',
                  'notes', 'estimated_cost', 'estimated_time', 'parts_needed',
                  'evaluated_at', 'images']
        read_only_fields = ['evaluated_at']

    def get_technician_name(self, obj):
        return obj.technician.get_full_name() or obj.technician.username
