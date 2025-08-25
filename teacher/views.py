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
    def get_permissions(self):
        if self.action in ['assign_teacher_details', 'get_all_teacher_assignments']:
            return [IsAuthenticated(), IsDirector()]
        elif self.action in ['list', 'create', 'retrieve','update', 'partial_update']:
            return [AllowAny()]
        return [IsAuthenticated()]

    
    
    @action(detail=False, methods=['post'], url_path='assign-teacher-details')
    def assign_teacher_details(self, request):
        teacher_id = request.data.get("teacher_id")
        print(teacher_id)
        yearlevel_id = request.data.get("yearlevel_id")
        print(yearlevel_id)
        subject_ids = request.data.get("subject_ids", [])
        period_ids = request.data.get("period_ids", [])
        print(period_ids)

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
        TeacherYearLevel.objects.get_or_create(teacher=teacher, yearlevel_id=yearlevel)

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
            'year_levels',
            'classperiod_set__start_time',
            'classperiod_set__end_time',
            'classperiod_set__subject',
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

            # Step 2: Assign each period to the FIRST year level from teacher's year_levels
            year_level_ids = list(yearlevel_map.keys())

            if not year_level_ids:
                continue  # skip if teacher has no assigned year level

            index = 0  # for round-robin assignment

            for period in teacher.classperiod_set.all():
                assigned_year_level_id = year_level_ids[index % len(year_level_ids)]
                yearlevel_map[assigned_year_level_id]["periods"].append({
                    'period_id': period.id,
                    'period_name': period.name,
                    'start_time': period.start_time.start_period_time.strftime("%H:%M") if period.start_time else None,
                    'end_time': period.end_time.end_period_time.strftime("%H:%M") if period.end_time else None,
                    'subject_id': period.subject.id,
                    'subject_name': period.subject.subject_name
                })
                index += 1

            # Step 3: Build teacher assignment response
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
    
    
  
from rest_framework import viewsets
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


from datetime import datetime
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class AllTeachersWithYearLevelsAPIView(APIView):
    def get(self, request):
        teachers = Teacher.objects.select_related('user').all()

        # Date filter
        date_value = request.GET.get('date_value')
        if date_value:
            try:
                target_date = datetime.strptime(date_value, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."},
                                status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.now().date()

        filter_status = request.GET.get('status', 'all').lower()

        result = []
        present_teachers = []

        # Step 1: Gather teacher data
        for teacher in teachers:
            year_levels = TeacherYearLevel.objects.filter(
                teacher=teacher
            ).select_related('year_level')

            year_level_data = [
                {
                    'id': yl.year_level.id,
                    'level_name': yl.year_level.level_name,
                    'level_order': yl.year_level.level_order
                } for yl in year_levels
            ]

            attendance = TeacherAttendance.objects.filter(
                teacher=teacher, date=target_date
            ).first()
            attendance_status = attendance.status if attendance else "not marked"

            if filter_status == 'present' and attendance_status != 'present':
                continue
            elif filter_status == 'absent' and attendance_status != 'absent':
                continue
            elif filter_status not in ['present', 'absent', 'all', '']:
                return Response({"error": "Invalid status filter"}, status=400)

            periods = ClassPeriod.objects.filter(
                teacher=teacher
            ).select_related('year_level', 'classroom', 'start_time', 'end_time', 'subject')

            period_data = [
                {
                    "id": period.id,
                    "subject": period.subject.subject_name,
                    "start_time": period.start_time.name if period.start_time else None,
                    "end_time": period.end_time.name if period.end_time else None,
                    "start_time_id": period.start_time.id if period.start_time else None,
                    "end_time_id": period.end_time.id if period.end_time else None,
                    "year_level": {
                        "id": period.year_level.id,
                        "level_name": period.year_level.level_name
                    },
                    "classroom": {
                        "id": period.classroom.id,
                        "room_name": period.classroom.room_name
                    }
                } for period in periods
            ]

            if attendance_status == "present":
                present_teachers.append({
                    "id": teacher.id,
                    "year_levels": [yl.year_level.id for yl in year_levels],
                    "periods": [(p.start_time.id if p.start_time else None,
                                 p.end_time.id if p.end_time else None) for p in periods],
                    "name": f"{teacher.user.first_name} {teacher.user.last_name}"
                })

            result.append({
                'id': teacher.id,
                'first_name': teacher.user.first_name,
                'last_name': teacher.user.last_name,
                'email': teacher.user.email,
                'phone_no': teacher.phone_no,
                'year_levels': year_level_data,
                'attendance': {
                    'date': str(target_date),
                    'status': attendance_status
                },
                # 'assigned_periods': period_data
            })

        # Step 2: Match absent teacher periods
        absent_matches = []
        seen_matches = set()

        for teacher in teachers:
            attendance = TeacherAttendance.objects.filter(
                teacher=teacher, date=target_date
            ).first()
            attendance_status = attendance.status if attendance else "not marked"

            if attendance_status == "absent":
                periods = ClassPeriod.objects.filter(
                    teacher=teacher
                ).select_related('year_level', 'classroom', 'start_time', 'end_time', 'subject')

                for period in periods:
                    period_key = (period.start_time.id if period.start_time else None,
                                  period.end_time.id if period.end_time else None)
                    year_level_id = period.year_level.id

                    match_found = False

                    # Step 2.1: Try same year level teachers first
                    for present_teacher in present_teachers:
                        if (year_level_id in present_teacher["year_levels"] and
                            period_key not in present_teacher["periods"]):
                            match_key = (teacher.id, present_teacher["id"], *period_key)
                            if match_key not in seen_matches:
                                seen_matches.add(match_key)
                                absent_matches.append({
                                    "absent_teacher": f"{teacher.user.first_name} {teacher.user.last_name}",
                                    "absent_subject": period.subject.subject_name,
                                    "matched_present_teacher": present_teacher["name"],
                                    "period_time": f"{period.start_time.name if period.start_time else None} - {period.end_time.name if period.end_time else None}",
                                    # "priority": "same year level",
                                    "year_level": {
                                        "id": period.year_level.id,
                                        "level_name": period.year_level.level_name
                                    }
                                })
                                match_found = True
                                break

                    # Step 2.2: If no match in same year level, try other teachers
                    if not match_found:
                        for present_teacher in present_teachers:
                            if (year_level_id not in present_teacher["year_levels"] and
                                period_key not in present_teacher["periods"]):
                                match_key = (teacher.id, present_teacher["id"], *period_key)
                                if match_key not in seen_matches:
                                    seen_matches.add(match_key)
                                    absent_matches.append({
                                        "absent_teacher": f"{teacher.user.first_name} {teacher.user.last_name}",
                                        "absent_subject": period.subject.subject_name,
                                        "matched_present_teacher": present_teacher["name"],
                                        "period_time": f"{period.start_time.name if period.start_time else None} - {period.end_time.name if period.end_time else None}",
                                        # "priority": "other year level",
                                        "year_level": {
                                            "id": period.year_level.id,
                                            "level_name": period.year_level.level_name
                                        }
                                    })
                                    break

        return Response({
            "teachers": result,
            "absent_period_matches": absent_matches
        }, status=status.HTTP_200_OK)





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

    