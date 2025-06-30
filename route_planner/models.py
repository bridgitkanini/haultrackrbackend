from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Trip(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='trips', null=True)
    current_location = models.CharField(max_length=255)
    pickup_location = models.CharField(max_length=255)
    dropoff_location = models.CharField(max_length=255)
    current_cycle_hours = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Trip from {self.current_location} to {self.dropoff_location}"

class RestStop(models.Model):
    STOP_TYPES = [
        ('REST', 'Rest Stop'),
        ('FUEL', 'Fuel Stop'),
        ('BOTH', 'Rest and Fuel Stop'),
    ]
    
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    coordinates = models.JSONField()  # Store as {lat: float, lng: float}
    type = models.CharField(max_length=4, choices=STOP_TYPES)
    amenities = models.JSONField(default=dict)  # Store available amenities
    trip = models.ForeignKey(Trip, related_name='rest_stops', on_delete=models.CASCADE)
    planned_arrival = models.DateTimeField()
    planned_departure = models.DateTimeField()
    
    class Meta:
        ordering = ['planned_arrival']
    
    def __str__(self):
        return f"{self.get_type_display()} at {self.name}"
        
    @property
    def duration(self):
        """Calculate planned duration of stop in hours"""
        delta = self.planned_departure - self.planned_arrival
        return delta.total_seconds() / 3600
