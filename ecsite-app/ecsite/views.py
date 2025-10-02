from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, status
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
)
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.core.management import call_command


# Disable CSRF check for this assigment
class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@api_view(["POST"])
def initialize_data(request):
    try:
        file_name = request.data.get("file", "MOCK_DATA.json")
        print(f"Initializing data from {file_name}")
        call_command("init_data", file=file_name)
        return Response(
            {"message": f"Data initialized successfully from {file_name}"},
            status=status.HTTP_200_OK,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


###############################################################################
## TODO: Implement the following views


class ItemViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response({"message": "List of items"}, status=status.HTTP_200_OK)


class CartViewSet(viewsets.ViewSet):
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(
            {"message": "List of items in the cart"}, status=status.HTTP_200_OK
        )

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def add(self, request):
        pass

    @csrf_exempt
    @action(detail=False, methods=["post"])
    def purchase(self, request):
        pass
