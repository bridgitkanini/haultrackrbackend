from django.db import models
from route_planner.models import Trip

# Create your models here.

class LogSheet(models.Model):
    trip = models.ForeignKey(Trip, related_name='log_sheets', on_delete=models.CASCADE)
    date = models.DateField()
    log_data = models.JSONField()  # Store the ELD log data
    
    def __str__(self):
        return f"Log for {self.date} - Trip {self.trip.id}"
