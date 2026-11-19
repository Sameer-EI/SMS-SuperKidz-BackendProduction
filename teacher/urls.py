from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . views import *


router = DefaultRouter()
router.register(r'teacher', TeacherView)
router.register(r'teacheryearlevel', TeacherYearLevelView, basename='teacheryearlevel')

urlpatterns = [
    path('', include(router.urls)),
    path('dropdown-teachers/', TeacherDropdownAPIView.as_view()),
    path('all-teachers/', AllTeachersWithYearLevelsAPIView.as_view()),
    path('substitute-assign/', SubstituteAssignmentView.as_view()),
    path('remove-substitute/', RemoveSubstitutionAPIView.as_view()),
    path('absent-teacher/', AbsentTeacherFreeReplacementAPIView.as_view()),
    path('available-substitutes/', AvailableSubstitutesAPIView.as_view()),
    # path('toggle-teacher-absence/', ToggleTeacherAbsenceAPIView.as_view()),
    path('class-timetable/', ClassTimetableView.as_view()),
    path('teacher-workload/', TeacherWorkloadView.as_view()),
    path('save-timetable-slot/', SaveTimetableSlotView.as_view()),
    path('clear-timetable-slot/', ClearTimetableSlotView.as_view()),
    path('subject-matrix/', SubjectAllocationMatrixView.as_view()),
]



# Clean API Endpoint,Description / Pattern Match
# http://127.0.0.1:8000/t/teacher/, List teachers
# http://127.0.0.1:8000/t/teacher/assign-teacher-details/, Assign teacher details
# http://127.0.0.1:8000/t/teacher/all-teacher-assignments/, Get all teacher assignments
# http://127.0.0.1:8000/t/teacher/teacher_my_profile/, Current teacher profile
# http://127.0.0.1:8000/t/teacher/<pk>/, Teacher detail view by PK
# http://127.0.0.1:8000/t/teacheryearlevel/, List teacher year levels
# http://127.0.0.1:8000/t/teacheryearlevel/<pk>/, Teacher year level detail
# http://127.0.0.1:8000/t/dropdown-teachers/, Dropdown selection endpoints
# http://127.0.0.1:8000/t/all-teachers/, Fetch all teachers
# http://127.0.0.1:8000/t/substitute-assign/, Assign substitute
# http://127.0.0.1:8000/t/remove-substitute/, Remove substitute
# http://127.0.0.1:8000/t/absent-teacher/, Absent teacher details
# http://127.0.0.1:8000/t/available-substitutes/, List available substitutes
# http://127.0.0.1:8000/t/class-timetable/, Class timetable
# http://127.0.0.1:8000/t/teacher-workload/, Teacher workload data
# http://127.0.0.1:8000/t/save-timetable-slot/, Save timetable slot
# http://127.0.0.1:8000/t/clear-timetable-slot/, Clear timetable slot
# http://127.0.0.1:8000/t/subject-matrix/, Subject matrix