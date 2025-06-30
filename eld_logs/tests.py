from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
from rest_framework.test import APITestCase
from rest_framework import status
import base64
from PIL import Image
from io import BytesIO
from django.contrib.auth.models import User
from django.urls import reverse

from .models import LogSheet, DutyStatusChange
from .services.log_generator import LogGenerator
from route_planner.models import Trip, RestStop


class LogSheetModelTests(TestCase):
    def setUp(self):
        # Create a test trip
        self.trip = Trip.objects.create(
            current_location="New York, NY",
            pickup_location="Chicago, IL",
            dropoff_location="Los Angeles, CA",
            current_cycle_hours=0,
        )

        # Create a test log sheet
        self.log_sheet = LogSheet.objects.create(
            trip=self.trip,
            date=timezone.now().date(),
            total_miles=500,
            starting_odometer=1000,
            ending_odometer=1500,
        )

        # Create some duty status changes
        self.status_changes = [
            DutyStatusChange.objects.create(
                log_sheet=self.log_sheet,
                status="ON",
                start_time=datetime.strptime("08:00", "%H:%M").time(),
                end_time=datetime.strptime("08:15", "%H:%M").time(),
                location="New York, NY",
                odometer=1000,
            ),
            DutyStatusChange.objects.create(
                log_sheet=self.log_sheet,
                status="D",
                start_time=datetime.strptime("08:15", "%H:%M").time(),
                end_time=datetime.strptime("12:15", "%H:%M").time(),
                location="New York, NY",
                odometer=1200,
            ),
        ]

    def test_total_driving_hours(self):
        """Test calculation of total driving hours"""
        self.assertEqual(self.log_sheet.total_driving_hours, 4.0)  # 4 hours of driving

    def test_total_on_duty_hours(self):
        """Test calculation of total on-duty hours"""
        self.assertEqual(
            self.log_sheet.total_on_duty_hours, 4.25
        )  # 4 hours driving + 15 min on-duty


class LogGeneratorTests(TestCase):
    def setUp(self):
        # Create a test trip with stops
        self.trip = Trip.objects.create(
            current_location="New York, NY",
            pickup_location="Chicago, IL",
            dropoff_location="Los Angeles, CA",
            current_cycle_hours=0,
        )

        # Create some rest stops
        current_time = timezone.now()
        self.stops = [
            RestStop.objects.create(
                trip=self.trip,
                name="Rest Stop 1",
                location="Cleveland, OH",
                coordinates={"lat": 41.4993, "lng": -81.6944},
                type="REST",
                planned_arrival=current_time + timedelta(hours=6),
                planned_departure=current_time + timedelta(hours=16),
            ),
            RestStop.objects.create(
                trip=self.trip,
                name="Fuel Stop 1",
                location="Chicago, IL",
                coordinates={"lat": 41.8781, "lng": -87.6298},
                type="FUEL",
                planned_arrival=current_time + timedelta(hours=20),
                planned_departure=current_time + timedelta(hours=21),
            ),
        ]

        self.generator = LogGenerator(self.trip)

    def test_trip_segmentation(self):
        """Test that trip is properly segmented based on stops"""
        segments = self.generator._calculate_trip_segments(self.stops)
        self.assertEqual(
            len(segments), 4
        )  # Should have 4 segments (drive, rest, drive, fuel)

    def test_log_generation(self):
        """Test generation of log sheets"""
        log_sheets = self.generator.generate_logs()
        self.assertTrue(len(log_sheets) > 0)

        # Check first log sheet has proper duty status changes
        first_log = log_sheets[0]
        status_changes = first_log.duty_status_changes.all()
        self.assertTrue(len(status_changes) > 0)

    def test_grid_generation(self):
        """Test generation of visual grid"""
        # Create a log sheet with known status changes
        log_sheet = LogSheet.objects.create(trip=self.trip, date=timezone.now().date())

        DutyStatusChange.objects.create(
            log_sheet=log_sheet,
            status="D",
            start_time=datetime.strptime("08:00", "%H:%M").time(),
            end_time=datetime.strptime("12:00", "%H:%M").time(),
            location="New York, NY",
            odometer=1000,
        )

        # Generate grid
        grid_image = self.generator.generate_grid(log_sheet)

        # Verify it's a valid base64 encoded PNG
        try:
            image_data = base64.b64decode(grid_image)
            image = Image.open(BytesIO(image_data))
            self.assertEqual(image.format, "PNG")
        except Exception as e:
            self.fail(f"Failed to decode grid image: {str(e)}")


class LogSheetAPITests(APITestCase):
    def setUp(self):
        # Create a user and authenticate
        self.username = "apitestuser"
        self.password = "testpass123"
        self.user = User.objects.create_user(
            username=self.username, password=self.password
        )
        # Obtain JWT token
        url = reverse("token_obtain_pair")
        response = self.client.post(
            url, {"username": self.username, "password": self.password}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Create test data
        self.trip = Trip.objects.create(
            current_location="New York, NY",
            pickup_location="Chicago, IL",
            dropoff_location="Los Angeles, CA",
            current_cycle_hours=0,
            user=self.user,  # Make sure the trip belongs to the authenticated user
        )

    def test_generate_logs_endpoint(self):
        """Test the log generation endpoint"""
        url = "/api/logs/generate_logs/"
        data = {"trip_id": self.trip.id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)

    def test_get_grid_endpoint(self):
        """Test the grid generation endpoint"""
        # Create a log sheet first
        log_sheet = LogSheet.objects.create(trip=self.trip, date=timezone.now().date())
        DutyStatusChange.objects.create(
            log_sheet=log_sheet,
            status="D",
            start_time=datetime.strptime("08:00", "%H:%M").time(),
            end_time=datetime.strptime("12:00", "%H:%M").time(),
            location="New York, NY",
            odometer=1000,
        )
        url = f"/api/logs/{log_sheet.id}/grid/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("grid_image", response.data)
        self.assertIn("content_type", response.data)
        self.assertEqual(response.data["content_type"], "image/png")
