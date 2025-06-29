from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from route_planner.models import Trip

# Create your models here.

class LogSheet(models.Model):
    trip = models.ForeignKey(Trip, related_name='log_sheets', on_delete=models.CASCADE)
    date = models.DateField()
    total_miles = models.FloatField(default=0)
    starting_odometer = models.FloatField(default=0)
    ending_odometer = models.FloatField(default=0)
    carrier_name = models.CharField(max_length=255, blank=True)
    carrier_address = models.CharField(max_length=255, blank=True)
    driver_signature = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['trip', 'date']

    def __str__(self):
        return f"Log for {self.date} - Trip {self.trip.id}"

    @property
    def total_driving_hours(self):
        return sum(
            status.duration_hours
            for status in self.duty_status_changes.filter(status='D')
        )

    @property
    def total_on_duty_hours(self):
        return sum(
            status.duration_hours
            for status in self.duty_status_changes.filter(status__in=['D', 'ON'])
        )

class DutyStatusChange(models.Model):
    STATUS_CHOICES = [
        ('OFF', 'Off Duty'),
        ('SB', 'Sleeper Berth'),
        ('D', 'Driving'),
        ('ON', 'On Duty Not Driving'),
    ]

    log_sheet = models.ForeignKey(
        LogSheet,
        related_name='duty_status_changes',
        on_delete=models.CASCADE
    )
    status = models.CharField(max_length=3, choices=STATUS_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    location = models.CharField(max_length=255)
    odometer = models.FloatField(
        validators=[MinValueValidator(0)]
    )
    remarks = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.get_status_display()} from {self.start_time} to {self.end_time}"

    @property
    def duration_hours(self):
        """Calculate duration in hours"""
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        if end_minutes < start_minutes:  # Handle midnight crossing
            end_minutes += 24 * 60
        return (end_minutes - start_minutes) / 60.0
