import logging
import traceback

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .models import ErrorLog


logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request = context.get("request")

    if response is None:
        if isinstance(exc, IntegrityError):
            response = Response(
                {"detail": "Some of the information is already in use. Please check the details and try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            logger.error(
                "Unhandled API exception",
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            response = Response(
                {"detail": "We couldn't complete your request. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        response.data = {"detail": "Please sign in to access this resource."}

    if request is not None:
        try:
            user = getattr(request, "user", None)
            ErrorLog.objects.create(
                user=user if user and user.is_authenticated else None,
                endpoint=request.path,
                method=request.method,
                status_code=response.status_code,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                traceback_info="".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                ),
            )
        except Exception:
            logger.exception("Failed to save API error log")

    return response
