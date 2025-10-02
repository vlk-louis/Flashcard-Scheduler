from django.contrib.auth import login
from django.http import HttpResponse

from assignment.models import User

import logging

logger = logging.getLogger(__name__)


# Skip Login step for this assignment
class MockLoginUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api"):
            username = request.headers.get("X-User-NAME")
            if username:
                logger.info(f"Mock login for user: {username}")
                try:
                    user = User.objects.get(username=username)
                    login(request, user)
                except User.DoesNotExist:
                    return HttpResponse(
                        "User not found or invalid credentials.", status=401
                    )
        response = self.get_response(request)
        return response
