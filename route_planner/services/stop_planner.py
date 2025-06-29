"""
Service for planning rest and fuel stops along a route
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from ..models import Trip, RestStop
from ...haultrackrbackend.config import (
    FUEL_STOP_INTERVAL_MILES,
    MAX_DRIVING_HOURS,
    REQUIRED_REST_HOURS
)

class StopPlanningError(Exception):
    """Base exception for stop planning errors"""
    pass

class StopPlanner:
    def __init__(self, trip: Trip, route_data: Dict):
        self.trip = trip
        self.route_data = route_data
        self.total_distance = route_data['distance'] / 1609.34  # Convert meters to miles
        self.total_duration = route_data['duration'] / 3600  # Convert seconds to hours
        
    def plan_stops(self) -> List[RestStop]:
        """
        Plan all necessary stops for the trip
        """
        try:
            # Calculate required stops
            fuel_stops = self._plan_fuel_stops()
            rest_stops = self._plan_rest_stops()
            
            # Merge and optimize stops
            all_stops = self._merge_stops(fuel_stops, rest_stops)
            
            # Create RestStop objects
            return self._create_stop_objects(all_stops)
            
        except Exception as e:
            raise StopPlanningError(f"Failed to plan stops: {str(e)}")
    
    def _plan_fuel_stops(self) -> List[Dict]:
        """
        Calculate required fuel stops based on distance
        """
        num_fuel_stops = int(self.total_distance / FUEL_STOP_INTERVAL_MILES)
        fuel_stops = []
        
        for i in range(1, num_fuel_stops + 1):
            distance_at_stop = i * FUEL_STOP_INTERVAL_MILES
            time_at_stop = (distance_at_stop / self.total_distance) * self.total_duration
            
            fuel_stops.append({
                'distance': distance_at_stop,
                'time': time_at_stop,
                'type': 'FUEL',
                'duration': 0.5  # 30 minutes for fueling
            })
        
        return fuel_stops
    
    def _plan_rest_stops(self) -> List[Dict]:
        """
        Calculate required rest stops based on HOS regulations
        """
        rest_stops = []
        current_driving_time = 0
        
        while current_driving_time < self.total_duration:
            # Add rest stop after MAX_DRIVING_HOURS
            if current_driving_time + MAX_DRIVING_HOURS < self.total_duration:
                distance_at_stop = (current_driving_time + MAX_DRIVING_HOURS) / self.total_duration * self.total_distance
                
                rest_stops.append({
                    'distance': distance_at_stop,
                    'time': current_driving_time + MAX_DRIVING_HOURS,
                    'type': 'REST',
                    'duration': REQUIRED_REST_HOURS
                })
                
                current_driving_time += MAX_DRIVING_HOURS + REQUIRED_REST_HOURS
            else:
                break
        
        return rest_stops
    
    def _merge_stops(self, fuel_stops: List[Dict], rest_stops: List[Dict]) -> List[Dict]:
        """
        Merge fuel and rest stops, combining when they're close to each other
        """
        all_stops = fuel_stops + rest_stops
        all_stops.sort(key=lambda x: x['distance'])
        merged_stops = []
        
        i = 0
        while i < len(all_stops):
            current_stop = all_stops[i].copy()
            
            # Look ahead for nearby stops
            while (i + 1 < len(all_stops) and 
                   abs(all_stops[i + 1]['distance'] - current_stop['distance']) < 50):  # Within 50 miles
                next_stop = all_stops[i + 1]
                # Merge stops
                current_stop['type'] = 'BOTH'
                current_stop['duration'] = max(current_stop['duration'], next_stop['duration'])
                i += 1
            
            merged_stops.append(current_stop)
            i += 1
        
        return merged_stops
    
    def _create_stop_objects(self, stops: List[Dict]) -> List[RestStop]:
        """
        Create RestStop objects from planned stops
        """
        stop_objects = []
        start_time = timezone.now()
        
        for stop in stops:
            # Calculate planned arrival time
            hours_from_start = stop['time']
            planned_arrival = start_time + timedelta(hours=hours_from_start)
            planned_departure = planned_arrival + timedelta(hours=stop['duration'])
            
            # Create RestStop object
            stop_obj = RestStop(
                trip=self.trip,
                type=stop['type'],
                location="To be determined",  # Would be filled by POI API
                coordinates={},  # Would be filled by POI API
                planned_arrival=planned_arrival,
                planned_departure=planned_departure,
                amenities={}  # Would be filled by POI API
            )
            stop_objects.append(stop_obj)
        
        return stop_objects 