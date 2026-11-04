from urllib import request
from django.shortcuts import render

# Create your views here.
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from attendance.models import Attendance, SchoolHoliday

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
from director.views import send_whatsapp_message 
# from permission import RoleBasedPermission
from attendance.views import Holiday
from director.utils import send_email_notification
from django.db import transaction


import logging
import re
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)
from rest_framework.views import APIView
from rest_framework import status
from django.utils import timezone
from .serializers import TeacherYearLevelSerializer
from director.permission import RoleBasedPermissionteacheryearlevel



class IsDirector(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        )



class TeacherView(viewsets.ModelViewSet):
    queryset = Teacher.objects.filter(is_active=True)
    serializer_class = TeacherSerializer


    filter_backends = [filters.SearchFilter]
    search_fields = ['user__email', 'user__first_name', 'phone_no']

    
    @action(detail=False, methods=['post'], url_path='assign-teacher-details')
    def assign_teacher_details(self, request):
        teacher_id = request.data.get("teacher_id")
        yearlevel_id = request.data.get("yearlevel_id")
        subject_ids = request.data.get("subject_ids", [])
        period_ids = request.data.get("period_ids", [])
        term_id = request.data.get("term_id")
        classroom_id = request.data.get("classroom_id")


        errors = []
        assigned = []
        to_create = []

        # ---- basic validations ----
        if not teacher_id:
            return Response({"error": "teacher_id is required."}, status=400)

        if not yearlevel_id:
            return Response({"error": "yearlevel_id is required."}, status=400)

        if not subject_ids:
            return Response({"error": "At least one subject_id is required."}, status=400)

        if not period_ids:
            return Response({"error": "At least one period_id is required."}, status=400)

        if len(subject_ids) != len(period_ids):
            return Response(
                {"error": "subject_ids and period_ids length must be equal."},
                status=400
            )
        
        if not term_id:
            return Response({"error": "term_id is required."}, status=400)

        if not classroom_id:
            return Response({"error": "classroom_id is required."}, status=400)

        term = Term.objects.filter(id=term_id).first()
        if not term:
            return Response({"error": "Invalid term_id."}, status=404)

        classroom = ClassRoom.objects.filter(id=classroom_id).first()
        if not classroom:
            return Response({"error": "Invalid classroom_id."}, status=404)


        # ---- fetch main objects ----
        teacher = Teacher.objects.filter(id=teacher_id).first()
        if not teacher:
            return Response({"error": "Invalid teacher_id."}, status=404)

        yearlevel = YearLevel.objects.filter(id=yearlevel_id).first()
        if not yearlevel:
            return Response({"error": "Invalid yearlevel_id."}, status=404)

        subjects = list(Subject.objects.filter(id__in=subject_ids))
        if len(subjects) != len(subject_ids):
            return Response({"error": "One or more invalid subject_ids."}, status=400)

        periods = list(Period.objects.filter(id__in=period_ids))
        if len(periods) != len(period_ids):
            return Response({"error": "One or more invalid period_ids."}, status=400)

        # ---- load limit check ----
        if ClassPeriod.objects.filter(teacher=teacher).count() + len(subjects) > 6:
            return Response(
                {"error": "Teacher cannot be assigned more than 6 periods."},
                status=400
            )

        # ---- main logic ----
        for subject, period in zip(subjects, periods):

            # duplicate check (class + period)
            # ---- teacher time conflict check ----
            if ClassPeriod.objects.filter(
                year_level=yearlevel,
                term=term,
                period=period
            ).exists():
                errors.append(
                    f"{yearlevel.level_name} already has a class scheduled "
                    f"on {period.name} ({period.start_period_time}-{period.end_period_time})."
                )
                continue

            if ClassPeriod.objects.filter(
                classroom=classroom,
                term=term,
                period=period
            ).exists():
                errors.append(
                    f"Classroom {classroom.room_name} is already occupied "
                    f"on {period.name} ({period.start_period_time}-{period.end_period_time})."
                )
                continue

            if ClassPeriod.objects.filter(teacher=teacher, period=period).exists():
                errors.append(
                    f"Teacher {teacher.user.first_name} {teacher.user.last_name} "
                    f"is already assigned to another class on {period.name} "
                    f"({period.start_period_time}-{period.end_period_time})."
                )
                continue

            if ClassPeriod.objects.filter(year_level=yearlevel, term=term, period=period).exists():
                return Response({"error": f"{yearlevel.level_name} already has a class assigned for {period.name}."}
                                ,status=400)

            to_create.append(ClassPeriod(
                teacher=teacher,
                subject=subject,
                year_level=yearlevel,
                period=period,
                term=term,
                classroom=classroom,
                name=f"{subject.subject_name} - {period.name}"
            ))

            assigned.append({
                "subject": subject.subject_name,
                "period": period.name
            })

        # ---- final checks ----
        if errors:
            return Response({"errors": errors}, status=400)

        if not to_create:
            return Response(
                {"error": "No assignments could be created."},
                status=400
            )

        # ---- save ----
        with transaction.atomic():
            ClassPeriod.objects.bulk_create(to_create)

        return Response({
            "message": "Teacher assigned successfully.",
            "teacher": f"{teacher.user.first_name} {teacher.user.last_name}",
            "year_level": yearlevel.level_name,
            "assigned_subjects_periods": assigned
        }, status=200)
   
   
    
    @action(detail=False, methods=['get'], url_path='all-teacher-assignments')
    def get_all_teacher_assignments(self, request):
        from django.db.models import Prefetch
    
        teachers = Teacher.objects.filter(is_active=True).prefetch_related(
            'year_levels',
            Prefetch(
                'assigned_periods',
                queryset=ClassPeriod.objects.select_related(
                    'subject', 'period', 'classroom', 'classroom__room_type'
                ).order_by('period__start_period_time')
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
            # if teacher got no year level, make a fallback bucket
            if not yearlevel_map:
                yearlevel_map["unassigned"] = {
                    "year_level_id": None,
                    "year_level_name": "Unassigned class",
                    "periods": []
                }
            year_level_ids = list(yearlevel_map.keys())
    
            # Step 2: Assign each period in sorted order (round-robin year_levels)
            index = 0
            for period in teacher.assigned_periods.all():
                assigned_year_level_id = year_level_ids[index % len(year_level_ids)]
                yearlevel_map[assigned_year_level_id]["periods"].append({
                    'period_id': period.id,
                    'period_name': period.name,
                    'start_time': period.period.start_period_time.strftime("%H:%M") if period.period else None,
                    'end_time': period.period.end_period_time.strftime("%H:%M") if period.period else None,
                    'subject_id': period.subject.id if period.subject else None,
                    'subject_name': period.subject.subject_name if period.subject else None,
                    'class_id': period.classroom.id if period.classroom else None,
                    'class_name': period.classroom.room_name if period.classroom else None,
                    'class_type': period.classroom.room_type.name if period.classroom and period.classroom.room_type else None,
                    'year_level_id': period.year_level_id,
                    'year_level_name': period.year_level.level_name if period.year_level else None
                })
                index += 1
    
            # Step 3: Build teacher assignment response
            teacher_name = teacher.user.get_full_name() if teacher.user else str(teacher)
            response_data.append({
                'teacher_id': teacher.id,
                'teacher_name': teacher_name,
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
    

    

class TeacherYearLevelView(viewsets.ModelViewSet):
    serializer_class = TeacherYearLevelSerializer
    queryset = TeacherYearLevel.objects.filter(teacher__is_active=True)
    permission_classes = [RoleBasedPermissionteacheryearlevel]

    def get_queryset(self):
        permission_instance = self.permission_classes[0]()
        return permission_instance.filter_queryset(self.request, super().get_queryset(), self)



class TeacherDropdownAPIView(APIView):
    """
    Returns list of active teachers with id, name, cadre, subject, display_name
    for easy rendering in dropdown selectors.
    """
    def get(self, request):
        teachers = Teacher.objects.filter(is_active=True).select_related('user', 'subject')
        serializer = TeacherDropdownSerializer(teachers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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
        teachers = Teacher.objects.filter(is_active=True).select_related('user', 'subject')

        if teacher_id:
            teachers = teachers.filter(id=teacher_id)
            if not teachers.exists():
                return Response({"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND)

        result = []

        for teacher in teachers:
            attendance = Attendance.objects.filter(teacher=teacher,marked_at=target_date).first()
            attendance_status = (attendance.get_status_display().lower() if attendance else "not marked")

            if filter_status != 'all':
                if attendance_status == "not marked":
                    continue
                if attendance_status != filter_status:
                    continue

            # Fetch all periods assigned to this teacher
            periods = ClassPeriod.objects.filter(teacher=teacher).select_related(
                'subject', 'year_level', 'period'
            ).order_by('year_level__id', 'period__start_period_time')

            # Group periods by year_level
            grouped = defaultdict(list)
            for p in periods:
                grouped[p.year_level].append({
                    "id": p.id,
                    "name": p.period_name or (p.period.name if p.period else "Period"),
                    "day_of_week": p.day_of_week,
                    "period_index": p.period_index,
                    "subject": p.subject.subject_name if p.subject else None
                })

            year_level_data = [
                {
                    "id": yl.id,
                    "level_name": yl.level_name,
                    "periods": grouped[yl]
                }
                for yl in grouped.keys() if yl is not None
            ]

            result.append({
                'id': teacher.id,
                'first_name': teacher.user.first_name if teacher.user else "",
                'last_name': teacher.user.last_name if teacher.user else "",
                'email': teacher.user.email if teacher.user else "",
                'phone_no': teacher.phone_no,
                'cadre': teacher.cadre,
                'subject_id': teacher.subject.id if teacher.subject else None,
                'subject_name': teacher.subject.subject_name if teacher.subject else None,
                'display_name': str(teacher),
                'year_levels': year_level_data,
                'attendance': {'date': str(target_date), 'status': attendance_status},
            })

        return Response({"count": len(result), "teachers": result}, status=status.HTTP_200_OK)



class AbsentTeacherFreeReplacementAPIView(APIView):
    def get(self, request):
        date_value = request.GET.get("date_value")
        teacher_id = request.GET.get("teacher_id")

        # ---- date handling ----
        try:
            target_date = (
                datetime.strptime(date_value, "%Y-%m-%d").date()
                if date_value else timezone.now().date()
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Day of week for target_date
        day_of_week = target_date.strftime("%A")

        # ---- attendance sets ----
        absent_ids = set(
            Attendance.objects.filter(
                marked_at=target_date,
                status="A"
            ).values_list("teacher_id", flat=True)
        )

        leave_ids = set(
            Attendance.objects.filter(
                marked_at=target_date,
                status="L"
            ).values_list("teacher_id", flat=True)
        )

        present_ids = set(
            Attendance.objects.filter(
                marked_at=target_date,
                status="P"
            ).values_list("teacher_id", flat=True)
        )

        # ---- inactive = absent + leave ----
        inactive_ids = absent_ids | leave_ids

        # ---- fetch inactive teachers having periods ----
        inactive_teachers_qs = Teacher.objects.filter(
            id__in=inactive_ids,
            assigned_periods__isnull=False,
            is_active=True
        ).distinct().select_related("user", "subject")

        if teacher_id:
            inactive_teachers_qs = inactive_teachers_qs.filter(id=teacher_id)

        if not inactive_teachers_qs.exists():
            return Response({"absent_teachers": []}, status=status.HTTP_200_OK)

        result = []

        for teacher in inactive_teachers_qs:
            teacher_status = "leave" if teacher.id in leave_ids else "absent"

            # ---- periods of inactive teacher ----
            periods = (
                ClassPeriod.objects
                .filter(teacher=teacher, day_of_week=day_of_week)
                .select_related("subject", "period", "year_level")
                .order_by("period_index")
            )
            # fallback if day_of_week not set specifically
            if not periods.exists():
                periods = (
                    ClassPeriod.objects
                    .filter(teacher=teacher)
                    .select_related("subject", "period", "year_level")
                    .order_by("period__start_period_time")
                )

            period_data = []

            for p in periods:
                # ---- teachers already busy in same time slot ----
                busy_teacher_ids = set(
                    ClassPeriod.objects.filter(
                        day_of_week=p.day_of_week,
                        period_index=p.period_index
                    ).values_list("teacher_id", flat=True)
                )

                # Also teachers already assigned as substitute during this period on this date
                sub_busy_teacher_ids = set(
                    SubstituteAssignment.objects.filter(
                        date=target_date,
                        period=str(p.period_index)
                    ).values_list("substitute_teacher_id", flat=True)
                )
                busy_teacher_ids |= sub_busy_teacher_ids

                # ---- free teachers = present - busy - inactive ----
                candidate_ids = present_ids - busy_teacher_ids - inactive_ids

                # ---- same class teachers ----
                same_class_teacher_ids = set(
                    ClassPeriod.objects.filter(
                        year_level=p.year_level
                    ).values_list("teacher_id", flat=True)
                )

                same_class_free_ids = candidate_ids & same_class_teacher_ids
                other_class_free_ids = candidate_ids - same_class_free_ids

                same_class_teachers_qs = (
                    Teacher.objects.filter(id__in=same_class_free_ids, is_active=True)
                    .select_related("user", "subject")
                    .order_by("user__first_name", "user__last_name")
                )

                other_teachers_qs = (
                    Teacher.objects.filter(id__in=other_class_free_ids, is_active=True)
                    .select_related("user", "subject")
                    .order_by("user__first_name", "user__last_name")
                )

                same_class_free_teachers = [
                    {
                        "id": t.id,
                        "first_name": t.user.first_name if t.user else "",
                        "last_name": t.user.last_name if t.user else "",
                        "email": t.user.email if t.user else "",
                        "cadre": t.cadre,
                        "subject": t.subject.subject_name if t.subject else None,
                        "display_name": str(t)
                    }
                    for t in same_class_teachers_qs
                ]

                other_class_free_teachers = [
                    {
                        "id": t.id,
                        "first_name": t.user.first_name if t.user else "",
                        "last_name": t.user.last_name if t.user else "",
                        "email": t.user.email if t.user else "",
                        "cadre": t.cadre,
                        "subject": t.subject.subject_name if t.subject else None,
                        "display_name": str(t)
                    }
                    for t in other_teachers_qs
                ]

                all_free_teachers = (
                    same_class_free_teachers + other_class_free_teachers
                )

                sub_assignment = (
                    SubstituteAssignment.objects
                    .filter(
                        absent_teacher=teacher,
                        date=target_date,
                        period=str(p.period_index)
                    )
                    .select_related("substitute_teacher__user", "substitute_teacher__subject")
                    .first()
                )
                if not sub_assignment:
                    sub_assignment = (
                        SubstituteAssignment.objects
                        .filter(
                            absent_teacher=teacher,
                            date=target_date,
                            period=str(p.id)
                        )
                        .select_related("substitute_teacher__user", "substitute_teacher__subject")
                        .first()
                    )

                substitute_teacher_data = None

                if sub_assignment:
                    sub_teacher = sub_assignment.substitute_teacher
                    substitute_teacher_data = {
                        "id": sub_teacher.id,
                        "name": f"{sub_teacher.user.first_name} {sub_teacher.user.last_name}".strip() if sub_teacher.user else "",
                        "email": sub_teacher.user.email if sub_teacher.user else "",
                        "cadre": sub_teacher.cadre,
                        "subject": sub_teacher.subject.subject_name if sub_teacher.subject else None,
                        "display_name": str(sub_teacher),
                    }

                period_data.append({
                    "period_id": p.id,
                    "period_index": p.period_index,
                    "period_name": p.period_name or (p.period.name if p.period else "Period"),
                    "day_of_week": p.day_of_week,
                    "subject": p.subject.subject_name if p.subject else None,
                    "year_level": p.year_level.level_name if p.year_level else None,
                    "year_level_id": p.year_level_id,
                    "same_class_free_teachers": same_class_free_teachers,
                    "other_class_free_teachers": other_class_free_teachers,
                    "all_free_teachers": all_free_teachers,
                    "substitute_teacher": substitute_teacher_data,
                })

            teacher_name = f"{teacher.user.first_name} {teacher.user.last_name}".strip() if teacher.user else str(teacher)
            result.append({
                "absent_teacher": {
                    "id": teacher.id,
                    "name": teacher_name,
                    "email": teacher.user.email if teacher.user else "",
                    "cadre": teacher.cadre,
                    "subject": teacher.subject.subject_name if teacher.subject else None,
                    "display_name": str(teacher),
                    "status": teacher_status,
                },
                "periods": period_data
            })

        return Response({"absent_teachers": result}, status=status.HTTP_200_OK)



class SubstituteAssignmentView(APIView):
    def get(self, request):
        date_value = request.GET.get('date_value')
        assignments = SubstituteAssignment.objects.all().select_related(
            'absent_teacher__user', 'absent_teacher__subject',
            'substitute_teacher__user', 'substitute_teacher__subject',
            'year_level'
        )
        if date_value:
            try:
                target_date = datetime.strptime(date_value, "%Y-%m-%d").date()
                assignments = assignments.filter(date=target_date)
            except ValueError:
                pass

        serializer = SubstituteAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    def post(self, request):
        data = request.data

        # normalize input
        if isinstance(data, dict):
            data = [data]

        assignments = []
        for item in data:
            absent_teacher_id = item.get("absent_teacher")
            substitute_teacher_id = item.get("substitute_teacher")
            period = item.get("period")
            year_level_id = item.get("year_level")
            date_val = item.get("date")
            day_of_week = item.get("day_of_week")
            reason = item.get("reason", "Casual Leave / Absent")

            if absent_teacher_id and substitute_teacher_id and absent_teacher_id == substitute_teacher_id:
                return Response(
                    {"errors": ["Invalid assignment: Absent teacher and substitute teacher cannot be the same."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not date_val:
                target_date = timezone.now().date()
            else:
                try:
                    target_date = datetime.strptime(str(date_val), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    target_date = timezone.now().date()

            # Find existing assignment if any for the same absent teacher, slot, date and year_level
            existing = SubstituteAssignment.objects.filter(
                absent_teacher_id=absent_teacher_id,
                period=str(period),
                date=target_date,
                year_level_id=year_level_id
            ).first()

            item_data = dict(item)
            item_data["date"] = target_date
            if not item_data.get("day_of_week") and day_of_week:
                item_data["day_of_week"] = day_of_week

            if existing:
                serializer = SubstituteAssignmentSerializer(existing, data=item_data, partial=True)
            else:
                serializer = SubstituteAssignmentSerializer(data=item_data)

            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            assignment_obj = serializer.save()
            assignments.append(assignment_obj)


        # notifications
        def notify(assignment):
            subject = "Substitute Teacher Assignment"
            message = (
                f"Dear Teacher,\n\n"
                f"On {assignment.date}, during Period {assignment.period},\n"
                f"{assignment.absent_teacher} is absent.\n"
                f"Substitute assigned: {assignment.substitute_teacher}.\n\n"
                f"Regards,\nSchool Admin"
            )

            try:
                if assignment.absent_teacher and getattr(assignment.absent_teacher, "user", None) and assignment.absent_teacher.user.email:
                    send_email_notification(
                        assignment.absent_teacher.user.email, subject, message
                    )
            except Exception as e:
                logger.error(f"Error sending email to absent teacher: {e}")

            try:
                if assignment.substitute_teacher and getattr(assignment.substitute_teacher, "user", None) and assignment.substitute_teacher.user.email:
                    send_email_notification(
                        assignment.substitute_teacher.user.email, subject, message
                    )
            except Exception as e:
                logger.error(f"Error sending email to substitute teacher: {e}")

            try:
                send_whatsapp_message(message)
            except Exception as e:
                logger.error(f"Error sending whatsapp message: {e}")

        for assignment in assignments:
            try:
                notify(assignment)
            except Exception as e:
                logger.error(f"Notification error for assignment {getattr(assignment, 'id', None)}: {e}")

        return Response(
            {
                "assignments": SubstituteAssignmentSerializer(assignments, many=True).data,
                "message": "Substitute assignment(s) created successfully",
            },
            status=status.HTTP_201_CREATED
        )


class RemoveSubstitutionAPIView(APIView):
    """
    Removes a substitute assignment by slot details (year_level_id, day_of_week, period_index, date)
    or by assignment id.
    """
    def post(self, request):
        assignment_id = request.data.get("assignment_id")
        year_level_id = request.data.get("year_level_id")
        period = str(request.data.get("period", ""))
        date_str = request.data.get("date")

        if assignment_id:
            deleted_count, _ = SubstituteAssignment.objects.filter(id=assignment_id).delete()
            return Response({"success": True, "message": "Substitution removed successfully."})

        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                target_date = timezone.now().date()
        else:
            target_date = timezone.now().date()

        qs = SubstituteAssignment.objects.filter(date=target_date)
        if year_level_id:
            qs = qs.filter(year_level_id=year_level_id)
        if period:
            qs = qs.filter(period=period)

        deleted_count, _ = qs.delete()
        return Response({"success": True, "deleted_count": deleted_count, "message": "Substitution removed."})


class AvailableSubstitutesAPIView(APIView):
    """
    Returns available free teachers for a specific day, period, and date.
    Checks:
    1. Teacher marked Present on target_date (or not marked absent/leave)
    2. Teacher not assigned to any class during (day_of_week, period_index)
    3. Teacher not already assigned substitute duty at that period on target_date
    """
    def get(self, request):
        date_value = request.GET.get("date_value")
        day_of_week = request.GET.get("day_of_week")
        period_index = request.GET.get("period_index")
        absent_teacher_id = request.GET.get("absent_teacher_id")

        try:
            target_date = datetime.strptime(date_value, "%Y-%m-%d").date() if date_value else timezone.now().date()
        except ValueError:
            target_date = timezone.now().date()

        if not day_of_week:
            day_of_week = target_date.strftime("%A")

        if period_index is not None:
            try:
                period_idx = int(period_index)
            except ValueError:
                period_idx = 0
        else:
            period_idx = 0

        # Absent / Leave teachers on target_date
        inactive_ids = set(
            Attendance.objects.filter(
                marked_at=target_date,
                status__in=["A", "L"]
            ).values_list("teacher_id", flat=True)
        )
        if absent_teacher_id:
            try:
                inactive_ids.add(int(absent_teacher_id))
            except ValueError:
                pass

        # Teachers busy with regular class in that slot
        busy_ids = set(
            ClassPeriod.objects.filter(
                day_of_week=day_of_week,
                period_index=period_idx
            ).values_list("teacher_id", flat=True)
        )

        # Teachers already assigned substitute on that date and period
        sub_busy_ids = set(
            SubstituteAssignment.objects.filter(
                date=target_date,
                period=str(period_idx)
            ).values_list("substitute_teacher_id", flat=True)
        )

        excluded_ids = inactive_ids | busy_ids | sub_busy_ids

        # Available teachers
        free_teachers = Teacher.objects.filter(
            is_active=True
        ).exclude(
            id__in=excluded_ids
        ).select_related('user', 'subject').order_by('user__first_name', 'user__last_name')

        result = [
            {
                "id": t.id,
                "name": f"{t.user.first_name} {t.user.last_name}".strip() if t.user else f"Teacher {t.id}",
                "cadre": t.cadre,
                "subject": t.subject.subject_name if t.subject else None,
                "display_name": str(t)
            }
            for t in free_teachers
        ]

        return Response({"available_teachers": result, "count": len(result)}, status=status.HTTP_200_OK)



# =========================================================================
# WEEKLY TIMETABLE APIS (Dynamic Period model lookup)
# =========================================================================

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def parse_slot_tags(slot_name):
    """
    Extracts all bracketed tags from a slot name.
    Example: 
      '[Girls][PCM] Physics - Class 12' -> ['Girls', 'PCM']
      '[Boys] Chemistry - Class 10'      -> ['Boys']
    """
    if slot_name and "[" in slot_name:
        return re.findall(r"\[(.*?)\]", slot_name)
    return []


def get_slot_tag_display(slot_name):
    """
    Returns single or composite tag string for API response.
    Example:
      '[Girls][PCM] Physics - Class 12' -> '[Girls][PCM]'
      '[Boys] Chemistry - Class 10'      -> 'Boys'
    """
    tags = parse_slot_tags(slot_name)
    if not tags:
        return None
    if len(tags) == 1:
        return tags[0]
    return "".join(f"[{t}]" for t in tags)


def build_slot_name(subject_name, class_name, tag=None):
    """
    Builds standardized slot name supporting single or composite tags.
    Examples:
      build_slot_name("Physics", "Class 12", "[Girls][PCM]") -> "[Girls][PCM] Physics - Class 12"
      build_slot_name("Maths", "Class 10", "Boys")          -> "[Boys] Maths - Class 10"
    """
    subj = subject_name if subject_name else "Period"
    if not tag or not str(tag).strip():
        return f"{subj} - {class_name}"

    raw = str(tag).strip()
    if "[" in raw:
        tags = re.findall(r"\[(.*?)\]", raw)
    elif "-" in raw:
        tags = [t.strip() for t in raw.split("-") if t.strip()]
    else:
        tags = [raw]

    prefix = "".join(f"[{t}]" for t in tags) + " "
    return f"{prefix}{subj} - {class_name}"


def get_dynamic_periods_list(school_year_id=None):
    """
    Dynamically loads periods from director.models.Period model.
    Falls back gracefully if no Period records are seeded in database.
    """
    qs = Period.objects.all()
    if school_year_id:
        qs = qs.filter(year_id=school_year_id)
    periods = list(qs.order_by('start_period_time'))

    if periods:
        result = []
        for idx, p in enumerate(periods):
            time_str = ""
            if p.start_period_time and p.end_period_time:
                s_str = p.start_period_time.strftime("%I:%M %p") if hasattr(p.start_period_time, "strftime") else str(p.start_period_time)
                e_str = p.end_period_time.strftime("%I:%M %p") if hasattr(p.end_period_time, "strftime") else str(p.end_period_time)
                time_str = f"{s_str} - {e_str}"
            result.append({
                "id": p.id,
                "index": idx,
                "name": p.name,
                "time": time_str
            })
        return result

    # Fallback default if no Period rows in DB
    return [
        {"id": None, "index": 0, "name": "1st Period", "time": "9:00 - 9:40"},
        {"id": None, "index": 1, "name": "2nd Period", "time": "9:40 - 10:20"},
        {"id": None, "index": 2, "name": "3rd Period", "time": "10:20 - 11:00"},
        {"id": None, "index": 3, "name": "4th Period", "time": "11:00 - 11:40"},
        {"id": None, "index": 4, "name": "5th Period", "time": "11:40 - 12:20"},
        {"id": None, "index": 5, "name": "6th Period", "time": "12:20 - 1:00"},
        {"id": None, "index": 6, "name": "7th Period", "time": "1:00 - 1:40"},
    ]


class ClassTimetableView(APIView):
    """
    Returns full 6-Day x Periods weekly grid for a specific class (YearLevel).
    Dynamically fetches Period model headers.
    Includes subject, assigned teacher, absent status (for target_date), and active substitution arrangements.
    """
    def get(self, request):
        year_level_id = request.GET.get('year_level_id')
        school_year_id = request.GET.get('school_year_id')
        date_str = request.GET.get('date')

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except ValueError:
            target_date = timezone.now().date()

        tag = request.GET.get('tag') or request.GET.get('section')
        today_day_name = target_date.strftime("%A")

        if not year_level_id:
            first_class = YearLevel.objects.first()
            if not first_class:
                return Response({"error": "No YearLevels defined."}, status=status.HTTP_404_NOT_FOUND)
            year_level_id = first_class.id
        else:
            try:
                year_level_id = int(year_level_id)
            except ValueError:
                return Response({"error": "Invalid year_level_id."}, status=status.HTTP_400_BAD_REQUEST)

        year_level = YearLevel.objects.filter(id=year_level_id).first()
        if not year_level:
            return Response({"error": "YearLevel not found."}, status=status.HTTP_404_NOT_FOUND)

        # Dynamic period headers from Period model
        period_headers = get_dynamic_periods_list(school_year_id)

        # Absent / Leave teachers map for target_date
        absent_attendances = Attendance.objects.filter(
            marked_at=target_date,
            status__in=["A", "L"]
        ).select_related('teacher')

        absent_teachers_map = {
            att.teacher_id: ("Medical Leave" if att.status == "L" else "Casual Leave / Absent")
            for att in absent_attendances if att.teacher_id
        }

        # Substitute arrangements for target_date
        arrangements_qs = SubstituteAssignment.objects.filter(
            date=target_date,
            year_level_id=year_level_id
        ).select_related(
            'absent_teacher__user', 'absent_teacher__subject',
            'substitute_teacher__user', 'substitute_teacher__subject'
        )

        arrangements_map = {}
        for arr in arrangements_qs:
            arrangements_map[str(arr.period)] = arr

        # Fetch all class periods for this class
        class_periods = ClassPeriod.objects.filter(
            year_level_id=year_level_id
        ).select_related('subject', 'teacher__user', 'teacher__subject', 'period')

        if tag and str(tag).strip() and str(tag).strip().lower() not in ["all", "combined"]:
            raw_tag = str(tag).strip()
            tags_to_match = re.findall(r"\[(.*?)\]", raw_tag) if "[" in raw_tag else [t.strip() for t in raw_tag.split("-") if t.strip()]
            for t in tags_to_match:
                class_periods = class_periods.filter(name__icontains=f"[{t}]")
        elif tag and str(tag).strip().lower() == "combined":
            class_periods = class_periods.filter(models.Q(name__isnull=True) | ~models.Q(name__startswith="["))

        periods_lookup = {}
        for cp in class_periods:
            key_idx = f"{cp.day_of_week}_{cp.period_index}"
            periods_lookup[key_idx] = cp
            if cp.period_id:
                periods_lookup[f"{cp.day_of_week}_pid_{cp.period_id}"] = cp

        schedule_grid = []

        for day in DAYS_ORDER:
            is_today = (day == today_day_name)
            periods_list = []

            for p_info in period_headers:
                p_idx = p_info["index"]
                p_name = p_info["name"]
                p_id = p_info.get("id")

                key = f"{day}_{p_idx}"
                slot_key = f"{year_level_id}_{day}_{p_idx}"

                cp = periods_lookup.get(key) or (periods_lookup.get(f"{day}_pid_{p_id}") if p_id else None)
                teacher = cp.teacher if cp else None
                subject = cp.subject if cp else None

                is_teacher_absent = bool(is_today and teacher and (teacher.id in absent_teachers_map))
                absence_reason = absent_teachers_map.get(teacher.id) if is_teacher_absent else None

                # Check arrangement
                arr = arrangements_map.get(str(p_idx)) or (arrangements_map.get(str(p_id)) if p_id else None) or arrangements_map.get(p_name)
                is_arrangement = bool(is_today and arr)

                arrangement_data = None
                if is_arrangement and arr:
                    sub_t = arr.substitute_teacher
                    abs_t = arr.absent_teacher
                    arrangement_data = {
                        "assignment_id": arr.id,
                        "substitute_teacher_id": sub_t.id,
                        "substitute_teacher_name": f"{sub_t.user.first_name} {sub_t.user.last_name}".strip() if sub_t.user else f"Teacher {sub_t.id}",
                        "substitute_teacher_subject": sub_t.subject.subject_name if sub_t.subject else None,
                        "substitute_teacher_cadre": sub_t.cadre,
                        "substitute_display_name": str(sub_t),
                        "absent_teacher_id": abs_t.id,
                        "absent_teacher_name": f"{abs_t.user.first_name} {abs_t.user.last_name}".strip() if abs_t.user else f"Teacher {abs_t.id}",
                        "reason": arr.reason or absence_reason or "Arrangement"
                    }

                teacher_data = None
                if teacher:
                    teacher_data = {
                        "id": teacher.id,
                        "name": f"{teacher.user.first_name} {teacher.user.last_name}".strip() if teacher.user else f"Teacher {teacher.id}",
                        "cadre": teacher.cadre,
                        "subject": teacher.subject.subject_name if teacher.subject else None,
                        "display_name": str(teacher)
                    }

                periods_list.append({
                    "period_id": p_id,
                    "period_index": p_idx,
                    "period_name": p_name,
                    "time": p_info["time"],
                    "slot_key": slot_key,
                    "class_period_id": cp.id if cp else None,
                    "subject": subject.subject_name if subject else None,
                    "subject_id": subject.id if subject else None,
                    "teacher": teacher_data,
                    "is_free": bool(not subject and not teacher),
                    "is_absent": bool(is_teacher_absent and not is_arrangement),
                    "absence_reason": absence_reason,
                    "is_arrangement": is_arrangement,
                    "arrangement": arrangement_data,
                    "tag": get_slot_tag_display(cp.name) if cp else None,
                })

            schedule_grid.append({
                "day": day,
                "is_today": is_today,
                "periods": periods_list
            })

        return Response({
            "year_level": {
                "id": year_level.id,
                "name": year_level.level_name
            },
            "tag": tag,
            "date": str(target_date),
            "today_day": today_day_name,
            "period_headers": period_headers,
            "schedule": schedule_grid
        }, status=status.HTTP_200_OK)


class TeacherWorkloadView(APIView):
    """
    Returns weekly workload schedule for a specific teacher.
    Dynamically fetches Period model headers.
    Shows assigned classes, substitute duties, and free periods.
    """
    def get(self, request):
        teacher_id = request.GET.get('teacher_id')
        school_year_id = request.GET.get('school_year_id')
        date_str = request.GET.get('date')

        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
        except ValueError:
            target_date = timezone.now().date()

        today_day_name = target_date.strftime("%A")

        if not teacher_id:
            first_teacher = Teacher.objects.filter(is_active=True).first()
            if not first_teacher:
                return Response({"error": "No active teachers found."}, status=status.HTTP_404_NOT_FOUND)
            teacher_id = first_teacher.id
        else:
            try:
                teacher_id = int(teacher_id)
            except ValueError:
                return Response({"error": "Invalid teacher_id."}, status=status.HTTP_400_BAD_REQUEST)

        teacher = Teacher.objects.filter(id=teacher_id).select_related('user', 'subject').first()
        if not teacher:
            return Response({"error": "Teacher not found."}, status=status.HTTP_404_NOT_FOUND)

        # Dynamic period headers from Period model
        period_headers = get_dynamic_periods_list(school_year_id)

        # Regular assigned periods
        assigned_periods = ClassPeriod.objects.filter(
            teacher_id=teacher_id
        ).select_related('year_level', 'subject', 'period')

        periods_map = {}
        for cp in assigned_periods:
            key_idx = f"{cp.day_of_week}_{cp.period_index}"
            periods_map[key_idx] = cp
            if cp.period_id:
                periods_map[f"{cp.day_of_week}_pid_{cp.period_id}"] = cp

        # Substitute assignments for target_date where this teacher is substitute
        sub_duties_qs = SubstituteAssignment.objects.filter(
            substitute_teacher_id=teacher_id,
            date=target_date
        ).select_related('year_level', 'absent_teacher__user')

        sub_duties_map = {}
        for sub in sub_duties_qs:
            sub_duties_map[str(sub.period)] = sub

        schedule_grid = []
        total_weekly_periods = assigned_periods.count()

        for day in DAYS_ORDER:
            is_today = (day == today_day_name)
            periods_list = []

            for p_info in period_headers:
                p_idx = p_info["index"]
                p_name = p_info["name"]
                p_id = p_info.get("id")

                key = f"{day}_{p_idx}"
                cp = periods_map.get(key) or (periods_map.get(f"{day}_pid_{p_id}") if p_id else None)
                sub = (sub_duties_map.get(str(p_idx)) or (sub_duties_map.get(str(p_id)) if p_id else None)) if is_today else None

                if sub:
                    periods_list.append({
                        "period_id": p_id,
                        "period_index": p_idx,
                        "period_name": p_name,
                        "time": p_info["time"],
                        "type": "substitute_duty",
                        "class_name": sub.year_level.level_name,
                        "subject": teacher.subject.subject_name if teacher.subject else "Arrangement",
                        "note": f"Substitute for {sub.absent_teacher.user.first_name} {sub.absent_teacher.user.last_name}".strip() if sub.absent_teacher.user else "Substitute Duty",
                        "is_free": False
                    })
                elif cp:
                    periods_list.append({
                        "period_id": p_id,
                        "period_index": p_idx,
                        "period_name": p_name,
                        "time": p_info["time"],
                        "type": "regular_class",
                        "class_name": cp.year_level.level_name,
                        "year_level_id": cp.year_level_id,
                        "subject": cp.subject.subject_name if cp.subject else (teacher.subject.subject_name if teacher.subject else "Subject"),
                        "is_free": False,
                        "tag": get_slot_tag_display(cp.name),
                    })
                else:
                    periods_list.append({
                        "period_id": p_id,
                        "period_index": p_idx,
                        "period_name": p_name,
                        "time": p_info["time"],
                        "type": "free",
                        "class_name": None,
                        "subject": "Free",
                        "is_free": True
                    })

            schedule_grid.append({
                "day": day,
                "is_today": is_today,
                "periods": periods_list
            })

        return Response({
            "teacher": {
                "id": teacher.id,
                "name": f"{teacher.user.first_name} {teacher.user.last_name}".strip() if teacher.user else f"Teacher {teacher.id}",
                "cadre": teacher.cadre,
                "subject": teacher.subject.subject_name if teacher.subject else None,
                "display_name": str(teacher),
                "total_weekly_periods": total_weekly_periods,
            },
            "date": str(target_date),
            "today_day": today_day_name,
            "period_headers": period_headers,
            "schedule": schedule_grid
        }, status=status.HTTP_200_OK)


class SaveTimetableSlotView(APIView):
    """
    Assigns or updates a specific period slot for a class.
    Supports gender/stream tagging (e.g. Boys, Girls, [Girls][PCM]).
    Checks teacher availability to avoid duplicate simultaneous assignments.
    """
    def post(self, request):
        year_level_id = request.data.get("year_level_id")
        day_of_week = request.data.get("day_of_week")
        period_index = request.data.get("period_index")
        period_id = request.data.get("period_id")
        subject_id = request.data.get("subject_id")
        teacher_id = request.data.get("teacher_id")
        period_name = request.data.get("period_name")
        tag = request.data.get("tag") or request.data.get("section")

        if not year_level_id or not day_of_week or (period_index is None and not period_id):
            return Response({"error": "year_level_id, day_of_week, and period_index/period_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            p_idx = int(period_index) if period_index is not None else 0
        except ValueError:
            p_idx = 0

        period_obj = None
        if period_id:
            period_obj = Period.objects.filter(id=period_id).first()
            if period_obj and not period_name:
                period_name = period_obj.name
        elif period_index is not None:
            period_obj = Period.objects.order_by('start_period_time')[p_idx:p_idx+1].first()
            if period_obj and not period_name:
                period_name = period_obj.name

        if not period_name:
            period_name = f"{p_idx + 1}th Period" if p_idx > 2 else ["1st Period", "2nd Period", "3rd Period"][p_idx] if p_idx < 3 else "Period"

        year_level = YearLevel.objects.filter(id=year_level_id).first()
        if not year_level:
            return Response({"error": "YearLevel not found."}, status=status.HTTP_404_NOT_FOUND)

        teacher = Teacher.objects.filter(id=teacher_id).first() if teacher_id else None
        subject = Subject.objects.filter(id=subject_id).first() if subject_id else None

        # Update or create slot query isolated by tag
        slot_qs = ClassPeriod.objects.filter(year_level=year_level, day_of_week=day_of_week)
        if period_obj:
            slot_qs = slot_qs.filter(models.Q(period=period_obj) | models.Q(period_index=p_idx))
        else:
            slot_qs = slot_qs.filter(period_index=p_idx)

        slot = None
        if tag and str(tag).strip() and str(tag).strip().lower() not in ["all", "combined"]:
            raw_tag = str(tag).strip()
            tags_to_match = re.findall(r"\[(.*?)\]", raw_tag) if "[" in raw_tag else [t.strip() for t in raw_tag.split("-") if t.strip()]
            for t in tags_to_match:
                slot_qs = slot_qs.filter(name__icontains=f"[{t}]")
            slot = slot_qs.first()
        else:
            slot = slot_qs.filter(models.Q(name__isnull=True) | ~models.Q(name__startswith="[")).first()

        # Conflict check: is teacher already assigned to any class/section during this slot?
        if teacher:
            conflict_filter = models.Q(day_of_week=day_of_week) & (
                models.Q(period_index=p_idx) | (models.Q(period=period_obj) if period_obj else models.Q())
            )
            conflict_qs = ClassPeriod.objects.filter(teacher=teacher).filter(conflict_filter)
            if slot:
                conflict_qs = conflict_qs.exclude(id=slot.id)

            if conflict_qs.exists():
                conflict_item = conflict_qs.first()
                conf_class = conflict_item.year_level
                conf_tag = get_slot_tag_display(conflict_item.name)
                tag_label = f" ({conf_tag})" if conf_tag else ""
                return Response({
                    "error": f"Conflict: {teacher} is already assigned to {conf_class.level_name}{tag_label} on {day_of_week}, {period_name}."
                }, status=status.HTTP_400_BAD_REQUEST)

        slot_name = build_slot_name(subject.subject_name if subject else None, year_level.level_name, tag)

        if slot:
            slot.subject = subject
            slot.teacher = teacher
            slot.period = period_obj
            slot.period_name = period_name
            slot.period_index = p_idx
            slot.name = slot_name
            slot.save()
        else:
            slot = ClassPeriod.objects.create(
                year_level=year_level,
                day_of_week=day_of_week,
                period=period_obj,
                period_index=p_idx,
                period_name=period_name,
                subject=subject,
                teacher=teacher,
                name=slot_name
            )

        saved_tag = get_slot_tag_display(slot.name) or tag
        return Response({
            "message": "Period assigned successfully.",
            "slot": {
                "id": slot.id,
                "year_level_id": year_level.id,
                "day_of_week": day_of_week,
                "period_id": period_obj.id if period_obj else None,
                "period_index": p_idx,
                "period_name": period_name,
                "subject": subject.subject_name if subject else None,
                "teacher": str(teacher) if teacher else None,
                "tag": saved_tag
            }
        }, status=status.HTTP_200_OK)


class ClearTimetableSlotView(APIView):
    """
    Clears period assignment for a slot, isolated by tag/section if provided.
    """
    def post(self, request):
        year_level_id = request.data.get("year_level_id")
        day_of_week = request.data.get("day_of_week")
        period_index = request.data.get("period_index")
        period_id = request.data.get("period_id")
        tag = request.data.get("tag") or request.data.get("section")

        if not year_level_id or not day_of_week or (period_index is None and not period_id):
            return Response({"error": "year_level_id, day_of_week, and period_index/period_id are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            p_idx = int(period_index) if period_index is not None else 0
        except ValueError:
            p_idx = 0

        qs = ClassPeriod.objects.filter(year_level_id=year_level_id, day_of_week=day_of_week)
        if period_id:
            qs = qs.filter(models.Q(period_id=period_id) | models.Q(period_index=p_idx))
        else:
            qs = qs.filter(period_index=p_idx)

        if tag and str(tag).strip() and str(tag).strip().lower() not in ["all", "combined"]:
            raw_tag = str(tag).strip()
            tags_to_match = re.findall(r"\[(.*?)\]", raw_tag) if "[" in raw_tag else [t.strip() for t in raw_tag.split("-") if t.strip()]
            for t in tags_to_match:
                qs = qs.filter(name__icontains=f"[{t}]")
        elif tag and str(tag).strip().lower() == "combined":
            qs = qs.filter(models.Q(name__isnull=True) | ~models.Q(name__startswith="["))

        qs.delete()

        # Also delete substitution for this slot if exists
        sub_qs = SubstituteAssignment.objects.filter(year_level_id=year_level_id)
        if period_id:
            sub_qs = sub_qs.filter(models.Q(period=str(period_id)) | models.Q(period=str(p_idx)))
        else:
            sub_qs = sub_qs.filter(period=str(p_idx))
        sub_qs.delete()

        return Response({"message": "Slot assignment cleared successfully."}, status=status.HTTP_200_OK)


class SubjectAllocationMatrixView(APIView):
    """
    Aggregates weekly timetable per class to display:
    Subject Name, Assigned Teacher, and Total Weekly Allocation Count.
    """
    def get(self, request):
        year_level_id = request.GET.get('year_level_id')

        if not year_level_id:
            first_class = YearLevel.objects.first()
            if not first_class:
                return Response({"error": "No YearLevels found."}, status=status.HTTP_404_NOT_FOUND)
            year_level_id = first_class.id
        else:
            try:
                year_level_id = int(year_level_id)
            except ValueError:
                return Response({"error": "Invalid year_level_id."}, status=status.HTTP_400_BAD_REQUEST)

        year_level = YearLevel.objects.filter(id=year_level_id).first()
        if not year_level:
            return Response({"error": "YearLevel not found."}, status=status.HTTP_404_NOT_FOUND)

        tag = request.GET.get('tag') or request.GET.get('section')
        slots = ClassPeriod.objects.filter(
            year_level_id=year_level_id,
            subject__isnull=False
        ).select_related('subject', 'teacher__user', 'teacher__subject')

        if tag and str(tag).strip() and str(tag).strip().lower() not in ["all", "combined"]:
            raw_tag = str(tag).strip()
            tags_to_match = re.findall(r"\[(.*?)\]", raw_tag) if "[" in raw_tag else [t.strip() for t in raw_tag.split("-") if t.strip()]
            for t in tags_to_match:
                slots = slots.filter(name__icontains=f"[{t}]")
        elif tag and str(tag).strip().lower() == "combined":
            slots = slots.filter(models.Q(name__isnull=True) | ~models.Q(name__startswith="["))

        subject_stats = {}

        for slot in slots:
            subj_id = slot.subject.id
            subj_name = slot.subject.subject_name

            if subj_id not in subject_stats:
                teacher = slot.teacher
                subject_stats[subj_id] = {
                    "subject_id": subj_id,
                    "subject_name": subj_name,
                    "teacher_id": teacher.id if teacher else None,
                    "teacher_name": f"{teacher.user.first_name} {teacher.user.last_name}".strip() if teacher and teacher.user else ("Unassigned" if not teacher else str(teacher)),
                    "teacher_cadre": teacher.cadre if teacher else None,
                    "teacher_subject": teacher.subject.subject_name if teacher and teacher.subject else None,
                    "teacher_display_name": str(teacher) if teacher else "Unassigned",
                    "weekly_periods_count": 0
                }
            subject_stats[subj_id]["weekly_periods_count"] += 1

        matrix = list(subject_stats.values())

        return Response({
            "year_level": {
                "id": year_level.id,
                "name": year_level.level_name
            },
            "matrix": matrix,
            "total_allocated_periods": sum(m["weekly_periods_count"] for m in matrix)
        }, status=status.HTTP_200_OK)
