import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestUserMeEndpoint:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("user-me")
        self.test_username = "testuser"
        self.user = User.objects.create_user(username=self.test_username)

    def test_me_endpoint_with_mock_middleware_authentication(self):
        """Test that user can authenticate via X-User-NAME header"""
        response = self.client.get(self.url, HTTP_X_USER_NAME=self.test_username)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {"username": self.test_username}

    def test_me_endpoint_with_non_existent_user_header(self):
        """Test that non-existent user in header returns 401"""
        response = self.client.get(self.url, HTTP_X_USER_NAME="nonexistentuser")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_endpoint_without_authentication(self):
        """Test that unauthenticated request returns 401"""
        response = self.client.get(self.url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data == {"error": "User not authenticated"}
