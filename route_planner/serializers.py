from rest_framework import serializers
from .models import Trip, RestStop
from eld_logs.serializers import LogSheetSerializer

class RestStopSerializer(serializers.ModelSerializer):
    duration = serializers.FloatField(read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model = RestStop
        fields = [
            'id',
            'name',
            'location',
            'coordinates',
            'type',
            'type_display',
            'amenities',
            'trip',
            'planned_arrival',
            'planned_departure',
            'duration'
        ]

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = '__all__'

class TripPlanSerializer(serializers.Serializer):
    """
    Serializer for the entire trip plan, combining trip info,
    route data, planned stops, and ELD logs.
    """
    trip = TripSerializer()
    route_data = serializers.JSONField()
    stops = RestStopSerializer(many=True)
    logs = LogSheetSerializer(many=True)

    def to_representation(self, instance):
        """
        Convert the instance dict into a final representation.
        """
        return {
            'trip': TripSerializer(instance['trip']).data,
            'route_data': instance['route_data'],
            'stops': RestStopSerializer(instance['stops'], many=True).data,
            'logs': LogSheetSerializer(instance['logs'], many=True).data
        }