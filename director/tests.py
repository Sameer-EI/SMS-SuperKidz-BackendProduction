from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from .serializers import AdmissionSerializer


class AdmissionSerializerValidationTests(SimpleTestCase):
    @patch("director.serializers.User.objects.all_including_inactive")
    def test_rejects_an_email_already_used_by_another_user(self, all_users):
        all_users.return_value.filter.return_value.exists.return_value = True

        with self.assertRaises(ValidationError) as error:
            AdmissionSerializer().validate({"student": {"email": "riya@gmail.com"}})

        self.assertIn("already registered", str(error.exception.detail))
