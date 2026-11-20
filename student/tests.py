from django.test import TestCase
from types import SimpleNamespace
from datetime import date

from director.models import Admission, SchoolYear, YearLevel
from student.models import Student, StudentYearLevel
from student.views import StudentView


class StudentDetailsSchoolYearFilterTests(TestCase):
    def setUp(self):
        self.previous_year = SchoolYear.objects.create(
            year_name="2025-2026",
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
        )
        self.selected_year = SchoolYear.objects.create(
            year_name="2026-2027",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
        )
        previous_level = YearLevel.objects.create(level_name="Pre Nursery", level_order=1)
        self.selected_level = YearLevel.objects.create(level_name="Nursery", level_order=2)

        self.previous_only_student = Student.objects.create()
        StudentYearLevel.objects.create(
            student=self.previous_only_student,
            level=previous_level,
            year=self.previous_year,
        )

        self.reenrolled_student = Student.objects.create()
        StudentYearLevel.objects.create(
            student=self.reenrolled_student,
            level=previous_level,
            year=self.previous_year,
        )
        StudentYearLevel.objects.create(
            student=self.reenrolled_student,
            level=self.selected_level,
            year=self.selected_year,
        )

    def test_school_year_filters_students_and_uses_matching_year_level(self):
        request = SimpleNamespace(
            query_params={"school_year_id": str(self.selected_year.id)}
        )

        response = StudentView().get_student_details(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [student["student_id"] for student in response.data],
            [self.reenrolled_student.id],
        )
        self.assertEqual(response.data[0]["school year"], "2026-2027")
        self.assertEqual(response.data[0]["class"], "Nursery")

    def test_without_school_year_uses_latest_student_year_level(self):
        request = SimpleNamespace(query_params={})

        response = StudentView().get_student_details(request)

        reenrolled_data = next(
            item for item in response.data
            if item["student_id"] == self.reenrolled_student.id
        )
        self.assertEqual(reenrolled_data["school year"], "2026-2027")
        self.assertEqual(reenrolled_data["class"], "Nursery")

    def test_level_id_filters_students_and_uses_matching_level_record(self):
        request = SimpleNamespace(
            query_params={"level_id": str(self.selected_level.id)}
        )

        response = StudentView().get_student_details(request)

        self.assertEqual(
            [student["student_id"] for student in response.data],
            [self.reenrolled_student.id],
        )
        self.assertEqual(response.data[0]["class"], "Nursery")
        self.assertEqual(response.data[0]["school year"], "2026-2027")

    def test_response_includes_admission_date_for_selected_school_year(self):
        admission = Admission.objects.create(
            student=self.reenrolled_student,
            year_level=self.selected_level,
            school_year=self.selected_year,
        )
        request = SimpleNamespace(
            query_params={"school_year_id": str(self.selected_year.id)}
        )

        response = StudentView().get_student_details(request)

        self.assertEqual(response.data[0]["admission_date"], admission.admission_date)

    def test_invalid_school_year_id_returns_bad_request(self):
        request = SimpleNamespace(query_params={"school_year_id": "not-an-id"})

        response = StudentView().get_student_details(request)

        self.assertEqual(response.status_code, 400)
