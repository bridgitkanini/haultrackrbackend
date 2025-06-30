from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework import status
import jwt
from django.conf import settings

# Create your tests here.


class JWTTokenPayloadTest(APITestCase):
    def setUp(self):
        self.username = "testuser"
        self.password = "testpass123"
        self.email = "test@example.com"
        self.user = User.objects.create_user(
            username=self.username, password=self.password, email=self.email
        )

    def test_jwt_token_contains_username(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(
            url, {"username": self.username, "password": self.password}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        access_token = response.data["access"]
        # Decode the JWT token (without verifying signature for test)
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256"],
        )
        self.assertIn("username", payload)
        self.assertEqual(payload["username"], self.username)
