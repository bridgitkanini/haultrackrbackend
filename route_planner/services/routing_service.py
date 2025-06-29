"""
Routing service for handling route calculations and geocoding
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from django.core.cache import cache
from django.conf import settings
from ..models import Trip
from ...haultrackrbackend.config import (
    OPENROUTE_API_KEY,
    OPENROUTE_BASE_URL,
    CACHE_TIMEOUT
)

class RoutingError(Exception):
    """Base exception for routing service errors"""
    pass

class GeocodingError(RoutingError):
    """Exception for geocoding related errors"""
    pass

class RouteCalculationError(RoutingError):
    """Exception for route calculation related errors"""
    pass

class RateLimitError(RoutingError):
    """Exception for rate limit related errors"""
    pass

class RoutingService:
    def __init__(self):
        self.api_key = OPENROUTE_API_KEY
        self.base_url = OPENROUTE_BASE_URL
        self.headers = {
            'Accept': 'application/json',
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }

    def _make_request(self, endpoint: str, method: str = 'GET', data: Dict = None) -> Dict:
        """
        Make a rate-limited request to the OpenRouteService API
        """
        url = f"{self.base_url}/{endpoint}"
        
        # Check rate limit cache
        cache_key = f"ors_rate_limit_{datetime.now().strftime('%Y%m%d%H')}"
        request_count = cache.get(cache_key, 0)
        
        if request_count >= 40:  # Limit to 40 requests per hour
            raise RateLimitError("Rate limit exceeded. Please try again later.")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers)
            else:
                response = requests.post(url, json=data, headers=self.headers)
            
            # Update rate limit counter
            cache.set(cache_key, request_count + 1, timeout=3600)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise RoutingError(f"API request failed: {str(e)}")

    def geocode_location(self, location_name: str) -> Tuple[float, float]:
        """
        Geocode a location name to coordinates
        """
        cache_key = f"geocode_{location_name}"
        cached_result = cache.get(cache_key)
        
        if cached_result:
            return cached_result
        
        try:
            response = self._make_request(
                f"geocode/search?text={location_name}"
            )
            
            if not response.get('features'):
                raise GeocodingError(f"Location not found: {location_name}")
            
            coordinates = response['features'][0]['geometry']['coordinates']
            cache.set(cache_key, coordinates, timeout=CACHE_TIMEOUT)
            
            return coordinates
            
        except Exception as e:
            raise GeocodingError(f"Geocoding failed for {location_name}: {str(e)}")

    def calculate_route(self, trip: Trip) -> Dict:
        """
        Calculate route for a trip including current location to pickup to dropoff
        """
        try:
            # Geocode all locations
            current_coords = self.geocode_location(trip.current_location)
            pickup_coords = self.geocode_location(trip.pickup_location)
            dropoff_coords = self.geocode_location(trip.dropoff_location)
            
            # Calculate route segments
            first_leg = self._calculate_route_segment(current_coords, pickup_coords)
            second_leg = self._calculate_route_segment(pickup_coords, dropoff_coords)
            
            # Combine route data
            total_distance = first_leg['distance'] + second_leg['distance']
            total_duration = (
                first_leg['duration'] +
                second_leg['duration'] +
                3600  # Add 1 hour for pickup
            )
            
            return {
                'distance': total_distance,
                'duration': total_duration,
                'legs': [first_leg, second_leg],
                'geometry': {
                    'leg1': first_leg['geometry'],
                    'leg2': second_leg['geometry']
                }
            }
            
        except Exception as e:
            raise RouteCalculationError(f"Route calculation failed: {str(e)}")

    def _calculate_route_segment(
        self,
        start_coords: Tuple[float, float],
        end_coords: Tuple[float, float]
    ) -> Dict:
        """
        Calculate a route segment between two points
        """
        data = {
            "coordinates": [start_coords, end_coords],
            "profile": "driving-hgv",  # Use HGV (Heavy Goods Vehicle) profile
            "preference": "recommended",
            "units": "mi",  # Use miles
            "geometry": True
        }
        
        try:
            response = self._make_request(
                "v2/directions/driving-hgv",
                method='POST',
                data=data
            )
            
            route = response['routes'][0]
            return {
                'distance': route['summary']['distance'],
                'duration': route['summary']['duration'],
                'geometry': route['geometry']
            }
            
        except Exception as e:
            raise RouteCalculationError(
                f"Route segment calculation failed: {str(e)}"
            ) 