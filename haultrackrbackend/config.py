"""
Configuration file for API keys and settings
"""

# OpenRouteService API Configuration
OPENROUTE_API_KEY = 'your_api_key_here'  # Replace with actual API key
OPENROUTE_BASE_URL = 'https://api.openrouteservice.org'

# Rest Stop API Configuration (for future use)
REST_STOP_API_KEY = 'your_api_key_here'  # Replace with actual API key

# Route Planning Configuration
FUEL_STOP_INTERVAL_MILES = 1000
MAX_DRIVING_HOURS = 11
MAX_ON_DUTY_HOURS = 14
REQUIRED_REST_HOURS = 10
MAX_WEEKLY_HOURS = 70

# Cache Configuration
CACHE_TIMEOUT = 3600  # 1 hour in seconds 