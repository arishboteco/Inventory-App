"""Custom exception handlers for the Inventory app's REST API."""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.http import Http404


def custom_exception_handler(exc, context):
    """Handle Django ValidationError as a REST framework validation error.

    For other exceptions, follow DRF's default behavior.
    """
    if isinstance(exc, DjangoValidationError):
        exc = DRFValidationError(detail=exc.messages)

    if isinstance(exc, Http404):
        return Response({"detail": "Not found."}, status=404)

    # Call REST framework's default exception handler to get the standard error response.
    response = exception_handler(exc, context)

    # If DRF handled the exception, return its response. Otherwise, return None
    # for a 500 server error.
    if response is not None:
        response.data["status_code"] = response.status_code

    return response
