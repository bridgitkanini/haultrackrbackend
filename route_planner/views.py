from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
import requests
import json
import math
from datetime import datetime, timedelta
from .models import Trip
from .serializers import TripSerializer
from eld_logs.models import LogSheet

# Create your views here.

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all()
    serializer_class = TripSerializer
    
    @action(detail=True, methods=['post'])
    def plan_route(self, request, pk=None):
        trip = self.get_object()
        
        # Call external mapping API to get route information
        # For example, using OpenRouteService (free)
        api_key = 'your_api_key'  # You'll need to sign up for a free API key
        
        # Get coordinates for locations (geocoding)
        # In a real app, you'd handle errors and edge cases
        current_coords = self._geocode_location(trip.current_location, api_key)
        pickup_coords = self._geocode_location(trip.pickup_location, api_key)
        dropoff_coords = self._geocode_location(trip.dropoff_location, api_key)
        
        # Get route between points
        route_data = self._get_route(current_coords, pickup_coords, dropoff_coords, api_key)
        
        # Calculate ELD logs based on route
        logs = self._generate_eld_logs(trip, route_data)
        
        return Response({
            'route': route_data,
            'logs': logs
        })
    
    def _geocode_location(self, location_name, api_key):
        # In a real app, add error handling
        url = f"https://api.openrouteservice.org/geocode/search?api_key={api_key}&text={location_name}"
        response = requests.get(url)
        data = response.json()
        # Return [longitude, latitude]
        return data['features'][0]['geometry']['coordinates']
    
    def _get_route(self, current_coords, pickup_coords, dropoff_coords, api_key):
        # First leg: current to pickup
        first_leg = self._get_route_segment(current_coords, pickup_coords, api_key)
        
        # Second leg: pickup to dropoff
        second_leg = self._get_route_segment(pickup_coords, dropoff_coords, api_key)
        
        # Combine route data
        combined_route = {
            'distance': first_leg['distance'] + second_leg['distance'],
            'duration': first_leg['duration'] + second_leg['duration'] + 3600,  # Add 1 hour (3600 seconds) for pickup
            'legs': [first_leg, second_leg],
            'fuel_stops': self._calculate_fuel_stops(first_leg['distance'] + second_leg['distance'])
        }
        
        return combined_route
    
    def _get_route_segment(self, start_coords, end_coords, api_key):
        url = "https://api.openrouteservice.org/v2/directions/driving-hgv"
        headers = {
            'Accept': 'application/json',
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }
        body = {
            "coordinates": [start_coords, end_coords],
            "radiuses": [-1, -1]
        }
        
        response = requests.post(url, json=body, headers=headers)
        data = response.json()
        
        route = data['routes'][0]
        return {
            'distance': route['summary']['distance'],  # in meters
            'duration': route['summary']['duration'],  # in seconds
            'geometry': route['geometry']
        }
    
    def _calculate_fuel_stops(self, total_distance_meters):
        # Convert meters to miles
        total_distance_miles = total_distance_meters / 1609.34
        
        # Calculate number of fuel stops (at least once every 1000 miles)
        num_fuel_stops = math.ceil(total_distance_miles / 1000)
        
        # Generate evenly spaced fuel stops
        fuel_stops = []
        for i in range(1, num_fuel_stops + 1):
            distance_at_stop = (i * 1000 * 1609.34) if i < num_fuel_stops else total_distance_meters
            fuel_stops.append({
                'distance': distance_at_stop,
                'distance_miles': distance_at_stop / 1609.34
            })
        
        return fuel_stops
    
    def _generate_eld_logs(self, trip, route_data):
        # Constants for HOS regulations
        MAX_DRIVING_HOURS = 11
        MAX_ON_DUTY_HOURS = 14
        REQUIRED_REST_HOURS = 10
        MAX_WEEKLY_HOURS = 70
        
        # Current time and cycle
        current_time = datetime.now()
        current_cycle_used = trip.current_cycle_hours
        remaining_cycle = MAX_WEEKLY_HOURS - current_cycle_used
        
        # Total drive time in hours
        total_drive_time = route_data['duration'] / 3600  # Convert seconds to hours
        
        # Account for pickup (1 hour) and dropoff (1 hour)
        total_on_duty_time = total_drive_time + 2
        
        # List to store daily logs
        daily_logs = []
        
        # Current state
        current_day = current_time.date()
        day_drive_time = 0
        day_on_duty_time = 0
        remaining_drive_time = MAX_DRIVING_HOURS
        remaining_on_duty_time = MAX_ON_DUTY_HOURS
        
        # Simulation variables
        simulation_time = current_time
        total_elapsed_drive_time = 0
        
        # Process each day until trip is complete
        while total_elapsed_drive_time < total_drive_time:
            # Create a new log sheet
            log_sheet = {
                'date': current_day.strftime('%Y-%m-%d'),
                'activities': [],
                'total_drive': 0,
                'total_on_duty': 0,
                'total_off_duty': 0
            }
            
            # Start with off-duty if this is not the first day
            if len(daily_logs) > 0:
                # Add off-duty for required rest
                log_sheet['activities'].append({
                    'status': 'OFF',
                    'start_time': '00:00',
                    'end_time': '08:00',  # 8 hours of the 10-hour break
                    'duration': 8
                })
                
                # Update simulation time
                simulation_time += timedelta(hours=8)
                day_off_duty_time = 8
                
                # Reset daily limits
                remaining_drive_time = MAX_DRIVING_HOURS
                remaining_on_duty_time = MAX_ON_DUTY_HOURS
            else:
                day_off_duty_time = 0
            
            # On-duty (not driving) for pre-trip inspection
            log_sheet['activities'].append({
                'status': 'ON',
                'start_time': simulation_time.strftime('%H:%M'),
                'end_time': (simulation_time + timedelta(minutes=15)).strftime('%H:%M'),
                'duration': 0.25
            })
            
            simulation_time += timedelta(minutes=15)
            day_on_duty_time += 0.25
            remaining_on_duty_time -= 0.25
            
            # Calculate how much driving can be done today
            available_drive_time = min(
                remaining_drive_time,
                remaining_on_duty_time,
                remaining_cycle,
                total_drive_time - total_elapsed_drive_time
            )
            
            if available_drive_time > 0:
                # Add driving activity
                drive_start_time = simulation_time
                simulation_time += timedelta(hours=available_drive_time)
                
                log_sheet['activities'].append({
                    'status': 'D',
                    'start_time': drive_start_time.strftime('%H:%M'),
                    'end_time': simulation_time.strftime('%H:%M'),
                    'duration': available_drive_time
                })
                
                day_drive_time += available_drive_time
                day_on_duty_time += available_drive_time
                total_elapsed_drive_time += available_drive_time
                remaining_drive_time -= available_drive_time
                remaining_on_duty_time -= available_drive_time
                remaining_cycle -= available_drive_time
            
            # Add pickup or dropoff if applicable
            if total_elapsed_drive_time >= route_data['legs'][0]['duration'] / 3600 and len(log_sheet['activities']) < 4:
                # Add pickup (1 hour)
                log_sheet['activities'].append({
                    'status': 'ON',
                    'start_time': simulation_time.strftime('%H:%M'),
                    'end_time': (simulation_time + timedelta(hours=1)).strftime('%H:%M'),
                    'duration': 1,
                    'location': trip.pickup_location,
                    'notes': 'Pickup'
                })
                
                simulation_time += timedelta(hours=1)
                day_on_duty_time += 1
                remaining_on_duty_time -= 1
            elif total_elapsed_drive_time >= total_drive_time:
                # Add dropoff (1 hour)
                log_sheet['activities'].append({
                    'status': 'ON',
                    'start_time': simulation_time.strftime('%H:%M'),
                    'end_time': (simulation_time + timedelta(hours=1)).strftime('%H:%M'),
                    'duration': 1,
                    'location': trip.dropoff_location,
                    'notes': 'Dropoff'
                })
                
                simulation_time += timedelta(hours=1)
                day_on_duty_time += 1
            
            # Add off-duty time at end of day if needed
            if simulation_time.hour < 24:
                off_duty_hours = 24 - simulation_time.hour - (1 if simulation_time.minute > 0 else 0)
                
                if off_duty_hours > 0:
                    log_sheet['activities'].append({
                        'status': 'OFF',
                        'start_time': simulation_time.strftime('%H:%M'),
                        'end_time': '24:00',
                        'duration': off_duty_hours
                    })
                    
                    day_off_duty_time += off_duty_hours
            
            # Update log sheet totals
            log_sheet['total_drive'] = day_drive_time
            log_sheet['total_on_duty'] = day_on_duty_time
            log_sheet['total_off_duty'] = day_off_duty_time
            
            # Add log sheet to daily logs
            daily_logs.append(log_sheet)
            
            # Move to next day
            current_day += timedelta(days=1)
            simulation_time = datetime.combine(current_day, datetime.min.time())
            day_drive_time = 0
            day_on_duty_time = 0
        
        # Save log sheets to database
        for log_data in daily_logs:
            LogSheet.objects.create(
                trip=trip,
                date=datetime.strptime(log_data['date'], '%Y-%m-%d').date(),
                log_data=log_data
            )
        
        return daily_logs
