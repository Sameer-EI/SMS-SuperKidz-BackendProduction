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
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from permission import RoleBasedPermission



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
    # def get_permissions(self):
    #     if self.action in ['assign_teacher_details', 'get_all_teacher_assignments']:
    #         return [IsAuthenticated(), IsDirector()]
    #     elif self.action in ['list', 'create', 'retrieve','update', 'partial_update']:
    #         return [AllowAny()]
    #     return [IsAuthenticated()]

    
    
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
                         year_level=yearlevel,
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
        from django.db.models import Prefetch

        teachers = Teacher.objects.prefetch_related(
            'year_levels',
            Prefetch(
                'assigned_periods',
                queryset=ClassPeriod.objects.select_related(
                    'subject', 'start_time', 'end_time'
                ).order_by('start_time__start_period_time')  # 👈 sort by start_time
            )
        ).select_related('user')

        response_data = []

        for teacher in teachers:
            # Step 1: Build yearlevel map
            yearlevel_map = {
                yl.id: {
                    "year_level_id": yl.id,
                    "year_level_name": yl.level_name,
                    "periods": []
                }
                for yl in teacher.year_levels.all()
            }

            # Step 2: Assign each period in sorted order (round-robin year_levels)
            year_level_ids = list(yearlevel_map.keys())
            if not year_level_ids:
                continue  # skip if teacher has no assigned year level

            index = 0
            for period in teacher.assigned_periods.all():
                assigned_year_level_id = year_level_ids[index % len(year_level_ids)]
                yearlevel_map[assigned_year_level_id]["periods"].append({
                    'period_id': period.id,
                    'period_name': period.name,
                    'start_time': period.start_time.start_period_time.strftime("%H:%M") if period.start_time else None,
                    'end_time': period.end_time.end_period_time.strftime("%H:%M") if period.end_time else None,
                    'subject_id': period.subject.id if period.subject else None,
                    'subject_name': period.subject.subject_name if period.subject else None
                })
                index += 1

            # Step 3: Build teacher assignment response
            response_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher.user.get_full_name() if teacher.user else str(teacher),
                'total_assigned_periods': teacher.assigned_periods.count(),
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
    
    
  
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import TeacherYearLevel
from .serializers import TeacherYearLevelSerializer
from permission import RoleBasedPermission

class TeacherYearLevelView(viewsets.ModelViewSet):
    serializer_class = TeacherYearLevelSerializer
    queryset = TeacherYearLevel.objects.all()
    permission_classes = [RoleBasedPermission]

    def get_queryset(self):
        # Permission class ke filter_queryset() ka use karo
        return self.permission_classes[0]().filter_queryset(self.request, super().get_queryset(), self)

    def get(self, request, *args, **kwargs):
        # Check if the token is present in the request
        if not request.META.get('HTTP_AUTHORIZATION'):
            return Response({"detail": "Token not given"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # If token is present, proceed with the normal get method
        return super().get(request, *args, **kwargs)





from collections import defaultdict
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

class AllTeachersWithYearLevelsAPIView(APIView):
    def get(self, request):
        date_value = request.GET.get('date_value')
        try:
            target_date = datetime.strptime(date_value, "%Y-%m-%d").date() if date_value else timezone.now().date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        filter_status = request.GET.get('status', 'all').lower()
        if filter_status not in ['present', 'absent', 'all']:
            return Response({"error": "Invalid status filter"}, status=status.HTTP_400_BAD_REQUEST)

        teacher_id = request.GET.get('teacher_id')
        teachers = Teacher.objects.select_related('user').all()

        if teacher_id:
            teachers = teachers.filter(id=teacher_id)
            if not teachers.exists():
                return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        result = []

        for teacher in teachers:
            attendance = TeacherAttendance.objects.filter(teacher=teacher, date=target_date).first()
            attendance_status = attendance.status.lower() if attendance else "not marked"

            if filter_status != 'all':
                if attendance_status == "not marked":
                    continue
                if attendance_status != filter_status:
                    continue

            #  Fetch all periods assigned to this teacher
            periods = ClassPeriod.objects.filter(teacher=teacher).select_related(
                'subject', 'year_level', 'start_time'
            ).order_by('year_level__id', 'start_time')

            # Group periods by year_level
            grouped = defaultdict(list)
            for p in periods:
                grouped[p.year_level].append({
                    "id": p.id,
                    "name": getattr(p.start_time, "name", p.start_time.strftime("%H:%M") if hasattr(p.start_time, "strftime") else None),
                    "subject": p.subject.subject_name if p.subject else None
                })

            year_level_data = [
                {
                    "id": yl.id,
                    "level_name": yl.level_name,
                    "periods": grouped[yl]
                }
                for yl in grouped.keys()
            ]

            result.append({
                'id': teacher.id,
                'first_name': teacher.user.first_name,
                'last_name': teacher.user.last_name,
                'email': teacher.user.email,
                'phone_no': teacher.phone_no,
                'year_levels': year_level_data,
                'attendance': {'date': str(target_date), 'status': attendance_status},
            })

        return Response({"count": len(result), "teachers": result}, status=status.HTTP_200_OK)















class AbsentTeacherFreeReplacementAPIView(APIView):
    def get(self, request):
        date_value = request.GET.get('date_value')
        teacher_id = request.GET.get('teacher_id')

        try:
            target_date = datetime.strptime(date_value, "%Y-%m-%d").date() if date_value else timezone.now().date()
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1) Absent & Present sets build
        absent_ids = set(
            TeacherAttendance.objects.filter(date=target_date, status__iexact="absent")
            .values_list("teacher_id", flat=True)
        )
        present_ids = set(
            TeacherAttendance.objects.filter(date=target_date, status__iexact="present")
            .values_list("teacher_id", flat=True)
        )

        # 2) Absent teachers list (only with assigned periods)
        absent_teachers_qs = Teacher.objects.filter(
            id__in=absent_ids,
            assigned_periods__isnull=False
        ).distinct().select_related("user")

        if teacher_id:
            absent_teachers_qs = absent_teachers_qs.filter(id=teacher_id)

        if not absent_teachers_qs.exists():
            return Response({"absent_teachers": []}, status=status.HTTP_200_OK)

        result = []

        for teacher in absent_teachers_qs:
            # 3) Absent teacher ke assigned periods
            periods = ClassPeriod.objects.filter(teacher=teacher)\
                .select_related("subject", "start_time", "year_level")\
                .order_by("start_time")

            period_data = []

            for p in periods:
                # 4) Busy teachers = jo isi time slot par kahin class le rahe hain
                busy_teacher_ids = set(
                    ClassPeriod.objects.filter(start_time=p.start_time)
                    .values_list("teacher_id", flat=True)
                )

                # 5) Free teachers = Present - busy - absent
                candidate_ids = present_ids - busy_teacher_ids - absent_ids

                # 6) Same class (year_level) ke teachers
                same_class_teacher_ids = set(
                    ClassPeriod.objects.filter(year_level=p.year_level)
                    .values_list("teacher_id", flat=True)
                )

                # 7) Divide into same class & other class
                same_class_free_ids = candidate_ids & same_class_teacher_ids
                other_class_free_ids = candidate_ids - same_class_free_ids

                # Querysets
                same_class_teachers_qs = Teacher.objects.filter(id__in=same_class_free_ids)\
                    .select_related("user")\
                    .order_by("user__first_name", "user__last_name")

                other_teachers_qs = Teacher.objects.filter(id__in=other_class_free_ids)\
                    .select_related("user")\
                    .order_by("user__first_name", "user__last_name")

                same_class_free_teachers = [
                    {
                        "id": t.id,
                        "first_name": t.user.first_name,
                        "last_name": t.user.last_name,
                        "email": t.user.email,
                    }
                    for t in same_class_teachers_qs
                ]

                other_class_free_teachers = [
                    {
                        "id": t.id,
                        "first_name": t.user.first_name,
                        "last_name": t.user.last_name,
                        "email": t.user.email,
                    }
                    for t in other_teachers_qs
                ]

                # 👇 merged free teachers list
                all_free_teachers = same_class_free_teachers + other_class_free_teachers

                period_data.append({
                    "period_id": p.id,
                    "period_name": getattr(p.start_time, "name", str(p.start_time)),
                    "subject": p.subject.subject_name if p.subject else None,
                    "year_level": p.year_level.level_name if p.year_level else None,
                    "same_class_free_teachers": same_class_free_teachers,
                    "other_class_free_teachers": other_class_free_teachers,
                    "all_free_teachers": all_free_teachers
                })

            result.append({
                "absent_teacher": {
                    "id": teacher.id,
                    "name": f"{teacher.user.first_name} {teacher.user.last_name}".strip(),
                    "email": teacher.user.email
                },
                "periods": period_data
            })

        return Response({"absent_teachers": result}, status=status.HTTP_200_OK)
























from datetime import date

from .models import TeacherAttendance
from teacher.models import Teacher

class TeacherAttendanceAPIView(APIView):

    def post(self, request):
        teacher_id = request.data.get('teacher_id')
        status_input = request.data.get('status')  # 'present' or 'absent'
        attendance_date = request.data.get('date', str(date.today()))  # optional

        if not teacher_id or not status_input:
            return Response({'error': 'teacher_id and status are required'}, status=400)

        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=404)

        # Check if already marked
        obj, created = TeacherAttendance.objects.update_or_create(
            teacher=teacher,
            date=attendance_date,
            defaults={'status': status_input}
        )

        return Response({
            'message': 'Attendance marked successfully',
            'teacher_id': teacher_id,
            'status': status_input,
            'date': attendance_date
        }, status=200)







class SubstituteAssignmentView(APIView):
    def get(self, request):
        assignments = SubstituteAssignment.objects.all()
        serializer = SubstituteAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data
        print(data)

        # Single dict -> wrap in list for iteration
        if isinstance(data, dict):
            data = [data]
            many = False
        else:
            many = True

        errors = []
        for item in data:
            absent_teacher = item.get("absent_teacher")
            period = item.get("period")
            date = item.get("date")

            if SubstituteAssignment.objects.filter(
                absent_teacher=absent_teacher,
                period=period,
                date=date
            ).exists():
                errors.append(
                    f"Duplicate found: Teacher {absent_teacher} already has substitute "
                    f"for {period} on {date}"
                )

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        # If single dict, unwrap data again before serializer
        serializer_data = data if many else data[0]

        serializer = SubstituteAssignmentSerializer(data=serializer_data, many=many)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

