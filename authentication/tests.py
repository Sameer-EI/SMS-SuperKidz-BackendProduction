from unittest.mock import patch

from django.db import IntegrityError
from django.test import RequestFactory, SimpleTestCase
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from .exception_handlers import custom_exception_handler
from .middleware import GlobalErrorLoggingMiddleware


class ProtectedTestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"detail": "success"})


class CustomExceptionHandlerTests(SimpleTestCase):
    def setUp(self):
        self.request = RequestFactory().post("/d/admission/")

    @patch("authentication.exception_handlers.ErrorLog.objects.create")
    def test_integrity_errors_return_a_safe_user_message(self, _create_error_log):
        response = custom_exception_handler(
            IntegrityError("private database detail"),
            {"request": self.request},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("already in use", response.data["detail"])
        self.assertNotIn("private database detail", response.data["detail"])

    @patch("authentication.exception_handlers.ErrorLog.objects.create")
    def test_unhandled_errors_return_a_generic_server_message(self, _create_error_log):
        response = custom_exception_handler(
            RuntimeError("private server detail"),
            {"request": self.request},
        )

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private server detail", response.data["detail"])

    @patch("authentication.exception_handlers.ErrorLog.objects.create")
    def test_unauthenticated_browser_request_returns_json_and_a_helpful_message(
        self, _create_error_log
    ):
        request = APIRequestFactory().get("/d/admission/", HTTP_ACCEPT="*/*")
        response = ProtectedTestView.as_view()(request)
        response.render()

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(
            response.data["detail"],
            "Please sign in to access this resource.",
        )

    @patch.object(GlobalErrorLoggingMiddleware, "log_error")
    @patch("authentication.middleware.logger.error")
    def test_middleware_returns_a_safe_response_for_unhandled_errors(
        self, _log_exception, _log_error
    ):
        def raise_error(_request):
            raise RuntimeError("private server detail")

        response = GlobalErrorLoggingMiddleware(raise_error)(self.request)

        self.assertEqual(response.status_code, 500)
        self.assertNotIn("private server detail", response.content.decode())
