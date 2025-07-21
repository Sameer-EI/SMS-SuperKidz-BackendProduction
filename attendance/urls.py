from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'multiple-attendance', MultipleAttendanceViewSet1, basename='MultipleAttendanceViewSet1')
router.register(r'api/report', AttendanceReportViewSet, basename='attendance-report')
router.register(r'director-dashboard', DirectorAttendanceDashboard, basename='attendance-text-summary')
router.register(r'teacher-dashboard', TeacherAttendanceDashboard, basename='teacher-student-attendance')
router.register(r'student-dashboard', StudentOwnAttendanceViewSet, basename='student-own-attendance')
router.register(r'guardian/attendance', GuardianChildrenAttendanceViewSet, basename='guardian-attendance')
router.register(r'attendance/mark-holidays', BulkHolidayAttendanceViewSet, basename='mark-holiday')


urlpatterns = [
    path('', include(router.urls)),
    path('teacher-classes/<int:teacher_id>/', TeacherYearLevelList.as_view(), name='teacher-classes')
]