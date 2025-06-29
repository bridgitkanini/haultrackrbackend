from rest_framework import serializers
from .models import LogSheet, DutyStatusChange

class DutyStatusChangeSerializer(serializers.ModelSerializer):
    duration_hours = serializers.FloatField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DutyStatusChange
        fields = [
            'id',
            'log_sheet',
            'status',
            'status_display',
            'start_time',
            'end_time',
            'location',
            'odometer',
            'remarks',
            'duration_hours',
            'created_at'
        ]

class LogSheetSerializer(serializers.ModelSerializer):
    duty_status_changes = DutyStatusChangeSerializer(many=True, read_only=True)
    total_driving_hours = serializers.FloatField(read_only=True)
    total_on_duty_hours = serializers.FloatField(read_only=True)
    
    class Meta:
        model = LogSheet
        fields = [
            'id',
            'trip',
            'date',
            'total_miles',
            'starting_odometer',
            'ending_odometer',
            'carrier_name',
            'carrier_address',
            'driver_signature',
            'notes',
            'duty_status_changes',
            'total_driving_hours',
            'total_on_duty_hours',
            'created_at',
            'updated_at'
        ]