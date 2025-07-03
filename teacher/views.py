from django.shortcuts import render

# Create your views here.
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import Teacher,TeacherYearLevel
from .serializers import *
# from .serializers import TeacherSerializer
from rest_framework import filters
from rest_framework.filters import SearchFilter
from rest_framework.decorators import action
from director.models import *
from django.db.models import Prefetch
from rest_framework.permissions import AllowAny, IsAuthenticated,BasePermission


class IsDirector(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        )



class TeacherView(viewsets.ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer


    filter_backends = [filters.SearchFilter]
    search_fields = ['user__email', 'user__first_name', 'phone_no']
    
    # ***************with out JWT******************
    def get_permissions(self):
        if self.action in ['assign_teacher_details', 'get_all_teacher_assignments']:
            return [IsAuthenticated(), IsDirector()]
        elif self.action in ['list', 'create', 'retrieve','update', 'partial_update']:
            return [AllowAny()]
        return [IsAuthenticated()]

    
    
    @action(detail=False, methods=['post'], url_path='assign-teacher-details')
    def assign_teacher_details(self, request):
        teacher_id = request.data.get("teacher_id")
        yearlevel_id = request.data.get("yearlevel_id")
        subject_ids = request.data.get("subject_ids", [])
        period_ids = request.data.get("period_ids", [])

        # Validate teacher
        if not teacher_id:
            return Response({"error": "teacher_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({"error": "Invalid teacher_id."}, status=status.HTTP_404_NOT_FOUND)

        # Validate year level
        if not yearlevel_id:
            return Response({"error": "yearlevel_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            yearlevel = YearLevel.objects.get(id=yearlevel_id)
        except YearLevel.DoesNotExist:
            return Response({"error": "Invalid yearlevel_id."}, status=status.HTTP_404_NOT_FOUND)

        # Validate subjects
        if not subject_ids:
            return Response({"error": "At least one subject_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        subjects = Subject.objects.filter(id__in=subject_ids)
        if subjects.count() != len(subject_ids):
            return Response({"error": "One or more invalid subject_ids."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate periods
        if not period_ids:
            return Response({"error": "At least one period_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        periods = Period.objects.filter(id__in=period_ids)
        if periods.count() != len(period_ids):
            return Response({"error": "One or more invalid period_ids."}, status=status.HTTP_400_BAD_REQUEST)

        # Check teacher's current period load
        existing_classperiods = ClassPeriod.objects.filter(teacher=teacher)
        if existing_classperiods.count() + len(subject_ids) > 6:
            return Response({"error": "Teacher cannot be assigned more than 6 periods."}, status=status.HTTP_400_BAD_REQUEST)

        # Prevent duplicate assignments of the same subject to the same period
        assigned = []
        for subject in subjects:
            # Ensure the teacher has only one period assigned for each subject
            subject_period_assigned = ClassPeriod.objects.filter(teacher=teacher, subject=subject).exists()
            if subject_period_assigned:
                return Response(
                    {"error": f"Teacher is already assigned {subject.subject_name} in a period."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            for period in periods:
                # Assign only one period for each subject per teacher
                if not ClassPeriod.objects.filter(teacher=teacher, subject=subject).exists():
                    # Assign the teacher to the subject and period
                    cp = ClassPeriod.objects.create(
                        teacher=teacher,
                        subject=subject,
                        term=Term.objects.first(),  
                        start_time=period,  # Assign Period instance to start_time
                        end_time=period,  # Assign Period instance to end_time
                        classroom=ClassRoom.objects.first(),  # Using the first available classroom
                        name=f"{subject.subject_name} - {period.name}"
                    )
                    assigned.append({
                        "subject": subject.subject_name,
                        "period": period.name,
                        "time": f"{period.start_period_time} - {period.end_period_time}"
                    })
                    break  # Assign only one period per subject for the teacher

        # Link teacher to year level
        TeacherYearLevel.objects.get_or_create(teacher=teacher, year_level=yearlevel)

        # Return detailed response
        return Response({
            "message": "Teacher assigned successfully.",
            "teacher": f"{teacher.user.first_name} {teacher.user.last_name}",
            "year_level": yearlevel.level_name,
            "assigned_subjects_periods": assigned
        }, status=status.HTTP_200_OK)


    @action(detail=False, methods=['get'], url_path='all-teacher-assignments')
    def get_all_teacher_assignments(self, request):
        teachers = Teacher.objects.prefetch_related(
            'year_levels',  # Fetch the teacher's YearLevel through the ManyToMany relationship
            'classperiod_set',  # Fetch periods associated with the teacher
        ).all()

        response_data = []

        for teacher in teachers:
            yearlevel_map = {}

            # Populating the yearlevel_map with available year levels for this teacher
            for tyl in teacher.year_levels.all():
                yearlevel_map[tyl.id] = {
                    "year_level_id": tyl.id,
                    "year_level_name": tyl.level_name,
                    "periods": []
                }

            # Process each period and categorize it into the corresponding year level
            for period in teacher.classperiod_set.all():
                matched = False
                for y_id in yearlevel_map:
                    # If the period matches a year level, assign it
                    if not matched:
                        yearlevel_map[y_id]["periods"].append({
                            'period_id': period.id,
                            'period_name': period.name,
                            'start_time': period.start_time.start_period_time.strftime("%H:%M") if period.start_time else None,
                            'end_time': period.end_time.end_period_time.strftime("%H:%M") if period.end_time else None,
                            'subject_id': period.subject.id,
                            'subject_name': period.subject.subject_name
                        })
                        matched = True
                        break

                # If no match (i.e., the period doesn't belong to any year level), we can skip it or handle it differently.
                if not matched:
                    
                    pass

            # Add the teacher's information to the response data
            response_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher.user.get_full_name() if teacher.user else str(teacher),
                'total_assigned_periods': teacher.classperiod_set.count(),
                'max_periods_allowed': 6,
                'assignments': list(yearlevel_map.values())
            })

        return Response(response_data, status=status.HTTP_200_OK)
    
    
    # ********************Jwt get/PUT***************
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='teacher_my_profile', permission_classes=[IsAuthenticated])
    def teacher_my_profile(self, request):
        user = request.user

        try:
            teacher = Teacher.objects.get(user=user)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher profile not found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(teacher, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": "Teacher profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(teacher)
        return Response(serializer.data, status=status.HTTP_200_OK)