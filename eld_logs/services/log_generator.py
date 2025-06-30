"""
Service for generating ELD logs and visual grids
"""
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from PIL import Image, ImageDraw
from io import BytesIO
import base64

from ..models import LogSheet, DutyStatusChange
from route_planner.models import Trip, RestStop

class LogGenerationError(Exception):
    """Base exception for log generation errors"""
    pass

class LogGenerator:
    GRID_WIDTH = 800
    GRID_HEIGHT = 400
    HOUR_WIDTH = GRID_WIDTH / 24
    STATUS_HEIGHT = GRID_HEIGHT / 4
    STATUS_COLORS = {
        'OFF': '#FFFFFF',  # White
        'SB': '#FFE4B5',  # Moccasin
        'D': '#90EE90',   # Light Green
        'ON': '#ADD8E6',  # Light Blue
    }

    def __init__(self, trip: Trip):
        self.trip = trip

    def generate_logs(self) -> List[LogSheet]:
        """
        Generate log sheets for the entire trip
        """
        try:
            # Get all stops in chronological order
            stops = RestStop.objects.filter(trip=self.trip).order_by('planned_arrival')
            
            # Calculate trip segments
            segments = self._calculate_trip_segments(stops)
            
            # Generate log sheets for each day
            log_sheets = []
            current_date = self.trip.created_at.date()
            
            for segment in segments:
                log_sheet = self._create_log_sheet(current_date, segment)
                log_sheets.append(log_sheet)
                current_date += timedelta(days=1)
            
            return log_sheets
            
        except Exception as e:
            raise LogGenerationError(f"Failed to generate logs: {str(e)}")

    def _calculate_trip_segments(self, stops: List[RestStop]) -> List[Dict]:
        """
        Break trip into daily segments considering stops
        """
        segments = []
        current_time = self.trip.created_at
        current_location = self.trip.current_location
        
        # Handle first segment (current location to first stop or destination)
        if not stops:
            segments.append({
                'start_location': self.trip.current_location,
                'end_location': self.trip.pickup_location,
                'start_time': current_time,
                'end_time': current_time + timedelta(hours=2),  # Estimated time
                'status_changes': [
                    {
                        'status': 'ON',
                        'duration': 0.25,  # 15 minutes pre-trip
                        'location': current_location
                    },
                    {
                        'status': 'D',
                        'duration': 1.75,  # Remaining time
                        'location': current_location
                    }
                ]
            })
            return segments

        # Process each stop
        for i, stop in enumerate(stops):
            # Add driving segment before stop
            drive_duration = (stop.planned_arrival - current_time).total_seconds() / 3600
            
            if drive_duration > 0:
                segments.append({
                    'start_location': current_location,
                    'end_location': stop.location,
                    'start_time': current_time,
                    'end_time': stop.planned_arrival,
                    'status_changes': [
                        {
                            'status': 'D',
                            'duration': drive_duration,
                            'location': current_location
                        }
                    ]
                })

            # Add stop segment
            stop_duration = (stop.planned_departure - stop.planned_arrival).total_seconds() / 3600
            stop_status = 'OFF' if stop.type == 'REST' else 'ON'
            
            segments.append({
                'start_location': stop.location,
                'end_location': stop.location,
                'start_time': stop.planned_arrival,
                'end_time': stop.planned_departure,
                'status_changes': [
                    {
                        'status': stop_status,
                        'duration': stop_duration,
                        'location': stop.location
                    }
                ]
            })
            
            current_time = stop.planned_departure
            current_location = stop.location

        return segments

    def _create_log_sheet(self, date: datetime.date, segment: Dict) -> LogSheet:
        """
        Create a log sheet for a specific day
        """
        # Create the log sheet
        log_sheet = LogSheet.objects.create(
            trip=self.trip,
            date=date,
            starting_odometer=0,  # Would be calculated from actual distance
            ending_odometer=0,    # Would be calculated from actual distance
        )
        
        # Create duty status changes
        current_time = datetime.combine(date, datetime.min.time())
        
        for change in segment['status_changes']:
            start_time = current_time.time()
            end_time = (current_time + timedelta(hours=change['duration'])).time()
            
            DutyStatusChange.objects.create(
                log_sheet=log_sheet,
                status=change['status'],
                start_time=start_time,
                end_time=end_time,
                location=change['location'],
                odometer=0,  # Would be calculated from actual distance
                remarks=f"Trip {self.trip.id}"
            )
            
            current_time += timedelta(hours=change['duration'])
        
        return log_sheet

    def generate_grid(self, log_sheet: LogSheet) -> str:
        """
        Generate a visual grid representation of the log sheet
        Returns base64 encoded PNG image
        """
        # Create new image with white background
        image = Image.new('RGB', (self.GRID_WIDTH, self.GRID_HEIGHT), 'white')
        draw = ImageDraw.Draw(image)
        
        # Draw vertical lines for hours
        for hour in range(25):
            x = hour * self.HOUR_WIDTH
            draw.line([(x, 0), (x, self.GRID_HEIGHT)], fill='black', width=1)
            if hour < 24:
                draw.text((x + 5, self.GRID_HEIGHT - 20), str(hour), fill='black')
        
        # Draw horizontal lines for status sections
        for i in range(5):
            y = i * self.STATUS_HEIGHT
            draw.line([(0, y), (self.GRID_WIDTH, y)], fill='black', width=1)
        
        # Draw status blocks
        status_changes = log_sheet.duty_status_changes.all()
        for status_change in status_changes:
            self._draw_status_block(draw, status_change)
        
        # Convert image to base64
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        return base64.b64encode(buffer.getvalue()).decode()

    def _draw_status_block(self, draw: ImageDraw, status_change: DutyStatusChange):
        """
        Draw a single status block on the grid
        """
        # Calculate coordinates
        start_x = status_change.start_time.hour * self.HOUR_WIDTH
        start_x += (status_change.start_time.minute / 60) * self.HOUR_WIDTH
        
        end_x = status_change.end_time.hour * self.HOUR_WIDTH
        end_x += (status_change.end_time.minute / 60) * self.HOUR_WIDTH
        
        # Determine y position based on status
        status_positions = {'OFF': 0, 'SB': 1, 'D': 2, 'ON': 3}
        top_y = status_positions[status_change.status] * self.STATUS_HEIGHT
        
        # Draw the block
        draw.rectangle(
            [(start_x, top_y), (end_x, top_y + self.STATUS_HEIGHT)],
            fill=self.STATUS_COLORS[status_change.status],
            outline='black'
        )