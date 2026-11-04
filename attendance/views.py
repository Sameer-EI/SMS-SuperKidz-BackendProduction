from django.contrib.admin import action
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from student.pagination import CreatePagination

from .models import  *
from .serializers import *
from django.utils.dateformat import format as date_format
from datetime import date,datetime, timedelta
from django.db.models import Count, Q, Value
from rest_framework.viewsets import ViewSet
from teacher.models import TeacherYearLevel
from student.models import Guardian,StudentGuardian, StudentYearLevel, Student
from django.shortcuts import get_object_or_404
import holidays
from director.views import send_whatsapp_message
from calendar import monthrange
from rest_framework.decorators import action
from django.db.models.functions import Concat

#payload for MultipleAttendance
# {
#     "teacher": 1,
#     "year_level": 6,
#     "marked_at": "2025-09-24",
#     "P": [1],
#     "A": [104, 105],
#     "L": [106]
# }

def calculate_working_days(start_date, end_date):
    """
    Calculate working days between start_date and end_date.

    Excludes:
    - Sundays
    - National/International holidays
    - School holidays
    """

    if start_date > end_date:
        return 0

    # Get Holiday date ranges
    holidays = Holiday.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    holiday_dates = set()

    for holiday in holidays:
        current_date = max(holiday.start_date, start_date)
        last_date = min(holiday.end_date, end_date)

        while current_date <= last_date:
            holiday_dates.add(current_date)
            current_date += timedelta(days=1)

    # Get SchoolHoliday dates
    school_holiday_dates = set(
        SchoolHoliday.objects.filter(
            date__range=[start_date, end_date]
        ).values_list("date", flat=True)
    )

    # # Get SchoolEvent date ranges
    # events = SchoolEvent.objects.filter(
    #     start_date__lte=end_date,
    #     end_date__gte=start_date
    # )
    # event_dates = set()
    # for event in events:
    #     current_date_event = max(event.start_date, start_date)
    #     last_date_event = min(event.end_date, end_date)
    #     while current_date_event <= last_date_event:
    #         event_dates.add(current_date_event)
    #         current_date_event += timedelta(days=1)

    working_days = 0
    current_date = start_date

    while current_date <= end_date:

        # Sunday
        if current_date.weekday() == 6:
            current_date += timedelta(days=1)
            continue

        # National / International holiday
        if current_date in holiday_dates:
            current_date += timedelta(days=1)
            continue

        # School holiday
        if current_date in school_holiday_dates:
            current_date += timedelta(days=1)
            continue

        # # School event
        # if current_date in event_dates:
        #     current_date += timedelta(days=1)
        #     continue

        working_days += 1
        current_date += timedelta(days=1)

    return working_days


class StudentAttendanceView(ModelViewSet):
    queryset = Attendance.objects.filter(student__isnull=False)
    serializer_class = StudentAttendanceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        teacher = validated_data.get("teacher")
        if not teacher and validated_data.get("teacher_id"):
            teacher = Teacher.objects.filter(Q(id=validated_data["teacher_id"]) | Q(user_id=validated_data["teacher_id"])).first()

        office_staff = validated_data.get("office_staff")
        if not office_staff and validated_data.get("office_staff_id"):
            office_staff = OfficeStaff.objects.filter(Q(id=validated_data["office_staff_id"]) | Q(user_id=validated_data["office_staff_id"])).first()

        year_level_id = validated_data["year_level_id"]
        marked_at = validated_data.get("marked_at", date.today())

        allowed_statuses = {"P", "A", "L"}
        created_records = []
        absent_leave_students = []

        for status_code in allowed_statuses:
            for sid in validated_data.get(status_code, []):
                if not Student.objects.filter(id=sid, is_active=True).exists():
                    return Response(
                        {"error": f"Active student not found (ID: {sid})"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                student = Student.objects.get(id=sid, is_active=True)
                """
                attendance = Attendance.objects.create(
                    student=student,
                    status=status_code,
                    marked_at=marked_at,
                    teacher=teacher,
                    year_level_id=year_level_id
                )
                """
                #21/9/2026
                attendance, created = Attendance.objects.update_or_create(
                    student=student,
                    marked_at=marked_at,
                    defaults={
                        "status": status_code,
                        "teacher": teacher,
                        "office_staff": office_staff,
                        "year_level_id": year_level_id,
                        }
                        )
                created_records.append(attendance)

                if status_code in ["A", "L"]:
                    absent_leave_students.append(student)

        # WhatsApp Notification
        for student in absent_leave_students:
            student_name = f"{student.user.first_name} {student.user.last_name}"

            msg = (
                f"Dear Parent,\n\n"
                f"{student_name} was marked as Absent "
                f"on {marked_at.strftime('%d-%m-%Y')}.\n"
                f"Kindly ensure regular attendance.\n\n"
                f"Regards,\nSchool Management"
            )

            send_whatsapp_message(msg)

        return Response(
            StudentAttendanceSerializer(created_records, many=True).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, pk=None):
        instance = self.get_object()  # gets by pk

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True  # allows PATCH behavior
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Attendance deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

    
    @action(detail=False,methods=["get"],url_path="register")
    def register(self, request):

        # 1. GET QUERY PARAMETERS

        year_level_id = request.query_params.get("year_level_id")
        date_param = request.query_params.get("date")
        search = request.query_params.get("search","").strip()

        # year_level_id is required
        if not year_level_id:
            return Response(
                {
                    "error": "year_level_id is required."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

       
        # 2. VALIDATE YEAR LEVEL

        year_level = YearLevel.objects.filter(
            id=year_level_id
        ).first()

        if not year_level:
            return Response(
                {
                    "error": "Invalid year_level_id."
                },
                status=status.HTTP_404_NOT_FOUND
            )

        
        # 3. PARSE DATE

        if date_param:
            try:
                target_date = date.fromisoformat(date_param)

            except ValueError:
                return Response(
                    {
                        "error": "Invalid date format. Use YYYY-MM-DD."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        else:
            target_date = date.today()

        
        # 4. FIND SCHOOL YEAR

        school_year = SchoolYear.objects.filter(start_date__lte=target_date,end_date__gte=target_date ).first()

        if not school_year:
            return Response(
                {
                    "error": "No school year found for this date."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

       
        # 5. FIND TERM

        term = Term.objects.filter(year=school_year,start_date__lte=target_date,end_date__gte=target_date).first()

        
        # 6. CHECK HOLIDAY

        national_holiday = Holiday.objects.filter(start_date__lte=target_date,end_date__gte=target_date).first()

        school_holiday = SchoolHoliday.objects.filter(date=target_date).first()

        # --------------------------------------------------
        # 7. DETERMINE SCHOOL DAY
        # --------------------------------------------------

        if target_date.weekday() == 6:

            is_school_day = False
            holiday_reason = "Sunday"

        elif national_holiday:

            is_school_day = False
            holiday_reason = national_holiday.title

        elif school_holiday:

            is_school_day = False
            holiday_reason = school_holiday.title

        else:

            is_school_day = True
            holiday_reason = None

        # --------------------------------------------------
        # 8. GET STUDENTS OF THIS CLASS
        # --------------------------------------------------

        student_levels = StudentYearLevel.objects.filter(level=year_level,year=school_year,student__is_active=True).select_related("student","student__user")
      
        # --------------------------------------------------
        # 9. SEARCH FILTER
        # --------------------------------------------------

        if search:
            student_levels = student_levels.annotate(
        full_name=Concat(
                    "student__user__first_name",
                    Value(" "),
                    "student__user__last_name"
                )
            )

            student_levels = student_levels.filter(
                Q(full_name__icontains=search)
                | Q(student__user__first_name__icontains=search)
                | Q(student__user__last_name__icontains=search)
                | Q(student__roll_number__icontains=search)
            )

        # --------------------------------------------------
        # 10. CREATE STUDENT DATA
        # --------------------------------------------------

        students_data = []

        present_count = 0
        absent_count = 0
        leave_count = 0
        unmarked_count = 0

        for student_level in student_levels:

            student = student_level.student

            # ----------------------------------------------
            # Student name
            # ----------------------------------------------

            if student.user:
                student_name = student.user.get_full_name()

            else:
                student_name = ""

            # ----------------------------------------------
            # Current day's attendance
            # ----------------------------------------------

            attendance = Attendance.objects.filter(
                student=student,
                marked_at=target_date
            ).first()

            if attendance:

                current_status = attendance.status
                attendance_id = attendance.id

                if current_status == "P":
                    present_count += 1

                elif current_status == "A":
                    absent_count += 1

                elif current_status == "L":
                    leave_count += 1

            else:

                current_status = None
                attendance_id = None

                unmarked_count += 1

            # ----------------------------------------------
            # TERM ATTENDANCE PERCENTAGE
            # ----------------------------------------------

            term_percentage = 0.0

            if term:

                total_working_days = calculate_working_days(
                    term.start_date,
                    min(term.end_date, target_date)
                )

                if total_working_days > 0:

                    present_days = Attendance.objects.filter(
                        student=student,
                        marked_at__gte=term.start_date,
                        marked_at__lte=min(term.end_date, target_date),
                        status="P"
                    ).count()

                    term_percentage = round(
                        (present_days / total_working_days) * 100,
                        1
                    )

            # ----------------------------------------------
            # ADD STUDENT
            # ----------------------------------------------

            students_data.append(
                {
                    "student_id": student.id,
                    "student_name": student_name,
                    "roll_number": student.roll_number,
                    "term_percentage": term_percentage,
                    "status": current_status,
                    "attendance_id": attendance_id,
                }
            )

        # --------------------------------------------------
        # 11. SUMMARY
        # --------------------------------------------------

        summary = {
            "total_students": len(students_data),
            "present": present_count,
            "absent": absent_count,
            "leave": leave_count,
            "unmarked": unmarked_count,
        }

        # --------------------------------------------------
        # 12. FINAL RESPONSE DATA
        # --------------------------------------------------

        response_data = {
            "year_level_id": year_level.id,
            "class_name": year_level.level_name,
            "date": target_date,
            "is_school_day": is_school_day,
            "holiday_reason": holiday_reason,
            "summary": summary,
            "students": students_data,
        }

        # --------------------------------------------------
        # 13. SERIALIZE RESPONSE
        # --------------------------------------------------

        serializer = StudentAttendanceRegisterSerializer(
            response_data
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK
        )


    @action(detail=False,methods=["get"], url_path="defaulters", pagination_class=CreatePagination,)
    def defaulters(self, request):

        # --------------------------------------------------
        # 1. GET QUERY PARAMETERS
        # --------------------------------------------------

        threshold_param = request.query_params.get("threshold", "75")
        year_level_param = request.query_params.get("year_level_id")

        # --------------------------------------------------
        # 2. VALIDATE THRESHOLD
        # --------------------------------------------------

        try:
            threshold = float(threshold_param)

        except ValueError:
            return Response(
                {
                    "error": "threshold must be a valid number."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if threshold < 0 or threshold > 100:
            return Response(
                {
                    "error": "threshold must be between 0 and 100."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # --------------------------------------------------
        # 3. FIND CURRENT SCHOOL YEAR
        # --------------------------------------------------

        today = date.today()

        school_year = SchoolYear.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if not school_year:
            return Response(
                {
                    "error": "No active school year found."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # --------------------------------------------------
        # 4. FIND CURRENT TERM
        # --------------------------------------------------

        term = Term.objects.filter(
            year=school_year,
            start_date__lte=today,
            end_date__gte=today
        ).first()

        if not term:
            return Response(
                {
                    "error": "No active term found."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # --------------------------------------------------
        # 5. CALCULATE WORKING DAYS
        # --------------------------------------------------

        calculation_end_date = min(
            term.end_date,
            today
        )

        total_working_days = calculate_working_days(
            term.start_date,
            calculation_end_date
        )

        # --------------------------------------------------
        # 6. GET STUDENTS
        # --------------------------------------------------

        student_levels = StudentYearLevel.objects.filter(
            year=school_year,
            student__is_active=True
        ).select_related(
            "student",
            "student__user",
            "level"
        )

        # --------------------------------------------------
        # 7. FILTER BY CLASS
        # --------------------------------------------------

        if year_level_param:

            if year_level_param.upper() != "ALL":

                try:
                    year_level_id = int(
                        year_level_param
                    )

                except ValueError:
                    return Response(
                        {
                            "error": (
                                "year_level_id must be "
                                "a valid ID or 'ALL'."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                student_levels = student_levels.filter(
                    level_id=year_level_id
                )

        # --------------------------------------------------
        # 8. FIND DEFAULTERS
        # --------------------------------------------------

        defaulters = []

        for student_level in student_levels:

            student = student_level.student

            # ----------------------------------------------
            # Attendance counts
            # ----------------------------------------------

            attendance_counts = Attendance.objects.filter(
                student=student,
                marked_at__gte=term.start_date,
                marked_at__lte=calculation_end_date
            ).values("status")

            days_present = 0
            days_absent = 0
            days_leave = 0

            for record in attendance_counts:

                if record["status"] == "P":
                    days_present += 1

                elif record["status"] == "A":
                    days_absent += 1

                elif record["status"] == "L":
                    days_leave += 1

            # ----------------------------------------------
            # Percentage
            # ----------------------------------------------

            if total_working_days > 0:

                term_percentage = round(
                    (
                        days_present
                        / total_working_days
                    ) * 100,
                    1
                )

            else:

                term_percentage = 0.0

            # ----------------------------------------------
            # Check threshold
            # ----------------------------------------------

            if term_percentage >= threshold:
                continue

            # ----------------------------------------------
            # Student name
            # ----------------------------------------------

            if student.user:

                student_name = (
                    student.user.get_full_name()
                )

            else:

                student_name = ""

            # ----------------------------------------------
            # Guardian
            # ----------------------------------------------

            guardian_name = student.father_name

            guardian_phone = student.contact_number

            # ----------------------------------------------
            # Add defaulter
            # ----------------------------------------------

            defaulters.append(
                {
                    "student_id": student.id,
                    "student_name": student_name,
                    "roll_number": student.roll_number,
                    "class_name": (
                        student_level.level.level_name
                    ),
                    "year_level_id": (
                        student_level.level.id
                    ),
                    "term_percentage": term_percentage,
                    "days_present": days_present,
                    "days_absent": days_absent,
                    "days_leave": days_leave,
                    "total_working_days": (
                        total_working_days
                    ),
                    "guardian_name": guardian_name,
                    "guardian_phone": guardian_phone,
                }
            )

        # --------------------------------------------------
        # 9. RESPONSE
        # --------------------------------------------------

        pagination_requested = any(
            parameter in request.query_params
            for parameter in ("limit", "offset")
        )
        page = self.paginate_queryset(defaulters) if pagination_requested else None

        if page is not None:
            response = self.get_paginated_response(page)
            response.data["threshold"] = threshold
            response.data["total_defaulters"] = len(defaulters)
            return response

        # Fallback if pagination isn't applied
        return Response(
            {
                "threshold": threshold,
                "total_defaulters": len(defaulters),
                "results": defaulters,
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False,methods=["post"],url_path="notify-parent")
    def notify_parent(self, request):

        serializer = NotifyParentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        student_id = serializer.validated_data["student_id"]
        custom_message = serializer.validated_data.get("custom_message")

        # Get active student
        student = get_object_or_404(
            Student,
            id=student_id,
            is_active=True
        )

        # Get student's guardian
        guardian_link = (
            StudentGuardian.objects
            .filter(student=student)
            .select_related(
                "guardian",
                "guardian__user"
            )
            .first()
        )

        # Get guardian phone number
        if guardian_link and guardian_link.guardian:
            phone = guardian_link.guardian.phone_no
        else:
            phone = student.contact_number

        # No phone number found
        if not phone:
            return Response(
                {
                    "success": False,
                    "message": (
                        "No phone number found for this "
                        "student's parent/guardian."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get student name
        if student.user:
            student_name = student.user.get_full_name()
        else:
            student_name = "Student"

        # Create message
        if custom_message:
            message_text = custom_message
        else:
            message_text = (
                f"Dear Parent/Guardian,\n\n"
                f"This is to notify you that your ward "
                f"{student_name}'s attendance is below 75%.\n"
                f"Please ensure regular attendance.\n\n"
                f"Regards,\n"
                f"School Administration"
            )

        # Send WhatsApp message
        whatsapp_result = send_whatsapp_message(
            message_text
        )
          
        if not whatsapp_result:
            return Response(
                {
                    "success": False,
                    "message": "Failed to send WhatsApp notification.",
                    "error": "No WhatsApp response received."
                    },
                    status=status.HTTP_502_BAD_GATEWAY
                )
        whatsapp_response = whatsapp_result[0]
        if whatsapp_response.get("status") == "failed":
            return Response(
                {
                    "success": False,
                    "message": "Failed to send WhatsApp notification.",
                    "error": whatsapp_response.get("error")
                    },
                    status=status.HTTP_502_BAD_GATEWAY
                )
        # Success response
        return Response(
            {
                "success": True,
                "message": (
                    f"Alert sent to parent of {student_name}."
                ),
                "recipient": phone,
                "whatsapp": whatsapp_response
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=False,methods=["get"],url_path="heat-map")
    def heat_map(self, request):
        # get Student Id
        student_id = request.query_params.get("student_id")
        if not student_id:
             return Response(
                 {
                      "success": False,
                      "error": "student_id is required."
                 },
                 status=status.HTTP_400_BAD_REQUEST
                )
        # Validate days parameter
        days_param = request.query_params.get("days", "30")
        try:
            days_count = int(days_param)
        except (ValueError, TypeError):
            return Response({
                 "success": False,
                 "error": "days must be a valid integer."
            }, status=status.HTTP_400_BAD_REQUEST)
        if days_count <= 0:
                    return Response({
                         "success": False,
                         "error": "days must be greater than 0."
                    }, status=status.HTTP_400_BAD_REQUEST)
        #optional for safety limits
        
        if days_count > 365:
            return Response({
                 "success": False,
                 "error": "days must be less than or equal to 365."
            }, status=status.HTTP_400_BAD_REQUEST)


        #GET Student
        student = get_object_or_404(Student.objects.select_related("user"), id=student_id, is_active=True)

        target_date_param = (
            request.query_params.get("target_date")
            or request.query_params.get("date")
            or request.query_params.get("marked_at")
        )
        if target_date_param:
            try:
                target_date = datetime.strptime(target_date_param, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return Response({
                    "success": False,
                    "error": "target_date must be in YYYY-MM-DD format."
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = date.today()

        #Find current school year
        school_year = (SchoolYear.objects.filter( start_date__lte=target_date  , end_date__gte=target_date ).first() )
        if not school_year:
            return Response({
                 "success": False,
                 "error": "No active school year found for target_date."
            }, status=status.HTTP_400_BAD_REQUEST)
        #Find current term
        term = (Term.objects.filter(year=school_year, start_date__lte=target_date, end_date__gte=target_date).first())
        if not term:
                    return Response({
                         "success": False,
                         "error": "No active term found for target_date."
                    }, status=status.HTTP_400_BAD_REQUEST)
        term_start = term.start_date
        term_end = min(term.end_date, target_date)

        total_working_days = calculate_working_days(term_start, term_end)

        attendance_qs = Attendance.objects.filter(student=student, marked_at__range=(term_start, term_end))
        present_days = attendance_qs.filter(status="P").count()

        absent_days = attendance_qs.filter(status="A").count()
    

        leave_days = attendance_qs.filter(status="L").count()
        if total_working_days > 0:
            percentage = round((present_days / total_working_days) * 100,1)
        else:
            percentage = 0.0
        

        student_year_level = StudentYearLevel.objects.filter(student=student, year=school_year).select_related("level").first()

        if student_year_level and student_year_level.level:
            class_name = student_year_level.level.level_name
        else:
            class_name = "N/A"

        if student.user:
            student_name = student.user.get_full_name()

            if not student_name.strip():
                student_name = f"Student #{student.id}"
        else:
            student_name = f"Student #{student.id}"

        roll_number = student.roll_number

        heat_map_start = target_date - timedelta(days=days_count - 1)
        heat_map_end = target_date
        heat_map_attendance = {
            item.marked_at: item
            for item in Attendance.objects.filter(
                student=student,
                marked_at__range=(heat_map_start, heat_map_end)
            )
        }
        holiday_ranges = list(Holiday.objects.filter(
            start_date__lte=heat_map_end,
            end_date__gte=heat_map_start
        ))
        school_holidays = list(SchoolHoliday.objects.filter(
            date__range=(heat_map_start, heat_map_end)
        ))
        event_ranges = list(SchoolEvent.objects.filter(
            start_date__lte=heat_map_end,
            end_date__gte=heat_map_start
        ))
        attendance_status_map = {
            "P": "Present",
            "A": "Absent",
            "L": "Leave",
        }

        def holiday_event_status(check_date):
            status_parts = []
            for holiday in holiday_ranges:
                if holiday.start_date <= check_date <= holiday.end_date:
                    status_parts.append(f"Holiday - {holiday.title}")
            for school_holiday in school_holidays:
                if school_holiday.date == check_date:
                    status_parts.append(f"Holiday - {school_holiday.title}")
            for event in event_ranges:
                if event.start_date <= check_date <= event.end_date:
                    status_parts.append(f"Event - {event.title}")
            return ", ".join(status_parts)

        heat_map_list = []

        for offset in range(days_count):
            current_date = heat_map_start + timedelta(days=offset)
            record = heat_map_attendance.get(current_date)
            if current_date < school_year.start_date:
                heat_map_status = "Session Not Started"
            elif record:
                heat_map_status = attendance_status_map.get(record.status, record.get_status_display())
            elif current_date.weekday() == 6:
                heat_map_status = "Sunday"
            else:
                heat_map_status = holiday_event_status(current_date) or "Not Marked"
            heat_map_list.append({
                "date": current_date,
                "status": heat_map_status
            })

        response_data = {
            "student_id": student.id,
            "student_name": student_name,
            "roll_number": roll_number,
            "class_name": class_name,
             "term_summary": {
                 "percentage": percentage,
                 "present_days": present_days,
                 "absent_days": absent_days,
                 "leave_days": leave_days,
                 "total_working_days": total_working_days
             },
            "heat_map": heat_map_list
        }
        serializer = StudentAttendanceHeatMapSerializer(response_data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class DirectorAttendanceDashboard(ViewSet):
    def list(self, request):
        date_str = request.query_params.get("date")
        try:
            if date_str:
                marked_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            else:
                marked_date = date.today()              
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Step 2: Get attendance summary
        total_students = Student.objects.filter(is_active=True).count()
        present_today = Attendance.objects.filter(marked_at=marked_date, status='P').count()
        overall_percentage = (present_today / total_students * 100) if total_students else 0

        today = date.today()

        current_year = SchoolYear.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).first()

        # Step 3: Class-wise breakdown
        class_wise_data = []
        all_classes = YearLevel.objects.all()

        for cls in all_classes:
            # Total students in this class (for current school year ideally)
            total_students_in_class = Student.objects.filter(
                is_active=True,
                student_year_levels__level=cls,
                student_year_levels__year=current_year
            ).distinct().count()

            # Present students in this class
            present_students = Attendance.objects.filter(
                marked_at=marked_date,
                status='P',
                student__student_year_levels__level=cls,
                student__student_year_levels__year=current_year
            ).distinct().count()

            percentage = (
                present_students / total_students_in_class * 100
                if total_students_in_class else 0
            )

            class_wise_data.append({
                "class_name": cls.level_name,
                "present": present_students,
                "total": total_students_in_class,
                "percentage": f"{percentage:.1f}%"
            })


        return Response({
            "date": marked_date.strftime("%Y-%m-%d"),
            "session":f"{current_year.start_date.year}-{current_year.end_date.year}",
            "overall_attendance": {
                "present": present_today,
                "total": total_students,
                "percentage": f"{overall_percentage:.1f}%"
            },
            "class_wise_attendance": class_wise_data
        })


class TeacherAttendanceDashboard(ViewSet):
    def list(self, request):
        today = date.today()
        date_str = request.query_params.get("date")
        selected_date = None

        if date_str:
            for fmt in ("%Y-%m-%d", "%Y-%d-%m", "%d-%m-%Y"):
                try:
                    selected_date = datetime.strptime(date_str, fmt).date()
                    break
                except ValueError:
                    continue
            if not selected_date:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
            month = selected_date.month
            year = selected_date.year
        else:
            try:
                month = int(request.query_params.get("month", today.month))
                year = int(request.query_params.get("year", today.year))
            except ValueError:
                month = today.month
                year = today.year

        class_name = request.query_params.get("class_name")

        # Monthly boundaries
        _, last_day_of_month = monthrange(year, month)
        monthly_start = date(year, month, 1)
        monthly_end = date(year, month, last_day_of_month)

        # School-year boundaries
        school_year = SchoolYear.objects.filter(
            start_date__lte=monthly_end,
            end_date__gte=monthly_start,
        ).order_by("start_date").first()

        if not school_year:
            school_year = SchoolYear.objects.filter(
                start_date__year=year
            ).first() or SchoolYear.objects.order_by("-start_date").first()

        if school_year:
            yearly_start = school_year.start_date
            yearly_end = school_year.end_date
        else:
            yearly_start = date(year, 1, 1)
            yearly_end = date(year, 12, 31)

        m_total_working_days = calculate_working_days(monthly_start, monthly_end)
        y_total_working_days = calculate_working_days(yearly_start, yearly_end)

        student_levels = StudentYearLevel.objects.filter(student__is_active=True)

        if class_name:
            student_levels = student_levels.filter(level__level_name__iexact=class_name)

        result = []

        for syl in student_levels:
            if not syl.student:
                continue
            attendance_qs = Attendance.objects.filter(student=syl.student)

            # Date status if filtered by date
            date_status = None
            if selected_date:
                rec = attendance_qs.filter(marked_at=selected_date).first()
                date_status = rec.status if rec else "Not Marked"

            # Monthly summary (filtered)
            monthly = attendance_qs.filter(marked_at__year=year, marked_at__month=month)
            m_present = monthly.filter(status='P').count()
            m_absent = monthly.filter(status='A').count()
            m_leave = monthly.filter(status='L').count()
            m_percentage = (m_present / m_total_working_days * 100) if m_total_working_days else 0.0

            # Yearly summary (filtered by school year)
            yearly = attendance_qs.filter(marked_at__range=(yearly_start, yearly_end))
            y_present = yearly.filter(status='P').count()
            y_absent = yearly.filter(status='A').count()
            y_leave = yearly.filter(status='L').count()
            y_percentage = (y_present / y_total_working_days * 100) if y_total_working_days else 0.0

            student_name = f"{syl.student.user.first_name} {syl.student.user.last_name}" if syl.student.user else "N/A"
            class_name_val = syl.level.level_name if syl.level else "N/A"

            student_data = {
                "student_name": student_name,
                "class_name": class_name_val,
                "filter_month": month,
                "filter_year": year,
                "monthly_percentage": round(m_percentage, 1),
                "yearly_percentage": round(y_percentage, 1),
                "monthly_summary": {
                    "present": m_present,
                    "absent": m_absent,
                    "leave": m_leave,
                    "total_days": m_total_working_days,
                    "not_marked": max(0, m_total_working_days - (m_present + m_absent + m_leave))
                },
                "yearly_summary": {
                    "present": y_present,
                    "absent": y_absent,
                    "leave": y_leave,
                    "total_days": y_total_working_days,
                    "not_marked": max(0, y_total_working_days - (y_present + y_absent + y_leave))
                }
            }
            if selected_date:
                student_data["filter_date"] = selected_date.strftime("%Y-%m-%d")
                student_data["attendance_status"] = date_status

            result.append(student_data)

        return Response(result)


class StudentOwnAttendanceViewSet(ViewSet):
    @staticmethod
    def calculate_working_days(start_date, end_date):
        """Return working days, excluding Sundays and configured holidays."""
        return calculate_working_days(start_date, end_date)

    def list(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response(
                {"detail": "Login required. Or use /student-dashboard/<student_id>/."},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
        # assumes Student has a OneToOne to User named "user"
        student = get_object_or_404(Student, user=request.user)
        return self.retrieve(request, pk=student.id)
    
    def retrieve(self, request, pk=None):
        today = date.today()

        date_str = request.query_params.get("date")
        
        try:
            month = int(request.query_params.get("month", today.month))
            year = int(request.query_params.get("year", today.year))
        except ValueError:
            return Response({"error": "Invalid month or year format."}, status=400)

        # ---- date parsing ----
        try:
            selected_date = (
                datetime.strptime(date_str, "%Y-%m-%d").date()
                if date_str else None
            )
        except ValueError:
            return Response(
                {"error": "Invalid date format. Use YYYY-MM-DD."},
                status=400
            )

        # ---- student ----
        student = get_object_or_404(Student.objects.select_related('user'), id=pk)
        attendance_qs = Attendance.objects.filter(student=student)

        # ---- latest class ----
        latest_attendance = attendance_qs.order_by("-marked_at").first()
        year_level_name = (
            latest_attendance.year_level.level_name
            if latest_attendance and latest_attendance.year_level
            else "N/A"
        )

        # ==================================================
        # DATE-WISE VIEW (if date is passed)
        # ==================================================
        if selected_date:
            day_qs = attendance_qs.filter(marked_at=selected_date)
            return Response({
                "student_name": f"{student.user.first_name} {student.user.last_name}",
                "year_level": year_level_name,
                "filter_date": selected_date.strftime("%Y-%m-%d"),
                "attendance": {
                    "present": day_qs.filter(status="P").count(),
                    "absent": day_qs.filter(status="A").count(),
                    "leave": day_qs.filter(status="L").count(),
                    "total": day_qs.count(),
                }
            })

        # ---- Find School Year based on the filtered month range ----
        month_start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)

        school_year = SchoolYear.objects.filter(
            start_date__lte=month_end,
            end_date__gte=month_start
        ).first()

        if not school_year:
            return Response(
                {"error": "No school year found matching the selected month and year range."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # ==================================================
        # MONTHLY SUMMARY
        # ==================================================
        monthly = attendance_qs.filter(marked_at__year=year, marked_at__month=month)
        m_present = monthly.filter(status='P').count()
        m_absent = monthly.filter(status='A').count()
        m_leave = monthly.filter(status='L').count()
        
        m_total_working_days = self.calculate_working_days(month_start, month_end)
        m_percentage = (m_present / m_total_working_days * 100) if m_total_working_days > 0 else 0.0

        # ==================================================
        # YEARLY SUMMARY (Pure School Year Boundaries)
        # ==================================================
        y_total_working_days = self.calculate_working_days(school_year.start_date, school_year.end_date)

        yearly = attendance_qs.filter(marked_at__range=(school_year.start_date, school_year.end_date))
        y_present = yearly.filter(status='P').count()
        y_absent = yearly.filter(status='A').count()
        y_leave = yearly.filter(status='L').count()
        
        y_percentage = (y_present / y_total_working_days * 100) if y_total_working_days > 0 else 0.0

        return Response({
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "year_level": year_level_name,
            "filter_month": month,
            "filter_year": year,
            "monthly_percentage": round(m_percentage, 1),
            "yearly_percentage": round(y_percentage, 1),
            "monthly_summary": {
                "present": m_present,
                "absent": m_absent,
                "leave": m_leave,
                "total_days": m_total_working_days,
                "not_marked": max(0, m_total_working_days - (m_present + m_absent + m_leave))
            },
            "yearly_summary": {
                "present": y_present,
                "absent": y_absent,
                "leave": y_leave,
                "total_days": y_total_working_days,
                "not_marked": max(0, y_total_working_days - (y_present + y_absent + y_leave))
            }
        })




class GuardianChildrenAttendanceViewSet(ViewSet):
    def list(self, request):
        guardian_id = request.query_params.get("guardian_id")
        if not guardian_id:
            return Response({"error": "guardian_id is required"}, status=400)

        try:
            guardian = Guardian.objects.get(id=guardian_id)
        except Guardian.DoesNotExist:
            return Response({"error": "Guardian not found"}, status=404)

        # Get optional month and year from query params
        today = date.today()
        try:
            month = int(request.query_params.get("month", today.month))
            year = int(request.query_params.get("year", today.year))
        except ValueError:
            return Response({"error": "Invalid month or year format"}, status=400)

        # Calculate absolute start and end dates for the true working days calculation
        # Monthly boundaries
        _, last_day_of_month = monthrange(year, month)
        monthly_start = date(year, month, 1)
        monthly_end = date(year, month, last_day_of_month)

        # School-year boundaries. A school year can span two calendar years, so
        # do not derive these dates from the requested calendar year.
        school_year = SchoolYear.objects.filter(
            start_date__lte=monthly_end,
            end_date__gte=monthly_start,
        ).order_by("start_date").first()

        if not school_year:
            return Response(
                {"error": "No school year found for the selected month and year."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        yearly_start = school_year.start_date
        yearly_end = school_year.end_date

        m_total = calculate_working_days(monthly_start, monthly_end)
        y_total = calculate_working_days(yearly_start, yearly_end)

        student_links = StudentGuardian.objects.filter(guardian=guardian, student__is_active=True).select_related('student__user')
        
        response_data = []

        for link in student_links:
            student = link.student
            if not student:
                continue
                
            try:
                year_level = StudentYearLevel.objects.select_related('level').get(student=student)
            except StudentYearLevel.DoesNotExist:
                continue

            # Monthly attendance breakdowns (Present / Absent / Leave status)
            monthly_qs = Attendance.objects.filter(
                student=student,
                marked_at__year=year,
                marked_at__month=month
            )
            m_present = monthly_qs.filter(status='P').count()
            m_absent = monthly_qs.filter(status='A').count()
            m_leave = monthly_qs.filter(status='L').count()
            m_percent = round((m_present / m_total) * 100, 1) if m_total > 0 else 0.0

            # Yearly attendance breakdowns
            yearly_qs = Attendance.objects.filter(
                student=student,
                marked_at__range=(yearly_start, yearly_end),
            )
            y_present = yearly_qs.filter(status='P').count()
            y_absent = yearly_qs.filter(status='A').count()
            y_leave = yearly_qs.filter(status='L').count()
            y_percent = round((y_present / y_total) * 100, 1) if y_total > 0 else 0.0

            student_name = f"{student.user.first_name} {student.user.last_name}" if student.user else "N/A"
            
            response_data.append({
                'student_name': student_name,
                'class_name': year_level.level.level_name if year_level.level else "N/A",
                'monthly_summary': {
                    "month": month,
                    "present": m_present,
                    "absent": m_absent,
                    "leave": m_leave,
                    "total_days": m_total,
                    "not_marked": max(0, m_total - (m_present + m_absent + m_leave)),
                    "percentage": f"{m_percent}%"
                },
                'yearly_summary': {
                    "year": year,
                    "present": y_present,
                    "absent": y_absent,
                    "leave": y_leave,
                    "total_days": y_total,
                    "not_marked": max(0, y_total - (y_present + y_absent + y_leave)),
                    "percentage": f"{y_percent}%"
                }
            })

        return Response({
            "guardian_id": guardian.id,
            "filter_month": month,
            "filter_year": year,
            "total_children": len(response_data),
            "children": response_data
        })



class FetchIndianHolidaysView(APIView):

    def get(self, request, *args, **kwargs):
        year = request.query_params.get('year')

        if not year or not str(year).isdigit():
            return Response({'error': 'Please provide a valid year (e.g., ?year=2025)'}, status=400)

        year = int(year)
        holidays_qs = SchoolHoliday.objects.filter(date__year=year).order_by('date')
        serializer = SchoolHolidaySerializer(holidays_qs, many=True)

        return Response({
            "year": year,
            "total": holidays_qs.count(),
            "holidays": serializer.data
        }, status=200)

    def post(self, request, *args, **kwargs):
        year = request.data.get('year')

        if not year or not str(year).isdigit():
            return Response(
                {'error': 'Please provide a valid year (e.g., { "year": 2025 })'},
                status=status.HTTP_400_BAD_REQUEST
            )

        year = int(year)
        india_holidays = holidays.India(years=year)
        created, skipped = 0, 0

        for date, name in india_holidays.items():
            if not SchoolHoliday.objects.filter(date=date).exists():
                SchoolHoliday.objects.create(
                    title=name,
                    date=date,
                    description=name
                )
                created += 1
            else:
                skipped += 1

        return Response({
            "message": f"{created} holidays added, {skipped} already existed.",
            "year": year
        }, status=status.HTTP_201_CREATED)
        
class SchoolEventViewSet(ModelViewSet):
    queryset = SchoolEvent.objects.all().order_by('start_date')
    serializer_class = SchoolEventSerializer

    def perform_create(self, serializer):
        # Save the new event
        event = serializer.save()



        # Prepare message
        message_text = (
            f"📅 New School Event: {event.title}\n"
            f"🗓 From {event.start_date} to {event.end_date}\n"
            f"📍 Location: {event.location if hasattr(event, 'location') else 'School Campus'}\n"
            f"Details: {event.description if hasattr(event, 'description') else 'No additional details'}"
        )


        send_whatsapp_message(message_text)

    
class MonthlyCalendarView(APIView):
    def get(self, request, *args, **kwargs):
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if not month or not year or not month.isdigit() or not year.isdigit():
            return Response(
                {"error": "Please provide valid month and year. Example: ?month=10&year=2025"},
                status=status.HTTP_400_BAD_REQUEST
            )

        month = int(month)
        year = int(year)

        # School holidays (single-day)
        school_holidays = SchoolHoliday.objects.filter(
            date__month=month, date__year=year
        ).order_by('date')
        school_holiday_data = SchoolHolidaySerializer(school_holidays, many=True).data

        # Multi-day holidays overlapping this month
        start_of_month = f"{year}-{month:02d}-01"
        end_of_month = f"{year}-{month:02d}-{monthrange(year, month)[1]}"
        holidays = Holiday.objects.filter(
            Q(start_date__lte=end_of_month) & Q(end_date__gte=start_of_month)
        ).order_by('-start_date')
        holiday_data = HolidaySerializer(holidays, many=True).data

        # School events
        events = SchoolEvent.objects.filter(
            start_date__year=year,
            start_date__month=month
        ).order_by('start_date')
        event_data = SchoolEventSerializer(events, many=True).data

        return Response({
            "year": year,
            "month": month,
            "school_holidays": school_holiday_data,
            "custom_holidays": holiday_data,
            "events": event_data
        }, status=status.HTTP_200_OK)
        
##-------------------------Whatsapp Message---------------------------
from twilio.rest import Client

class SendWhatsAppView(APIView):
    def post(self, request):
        account_sid = 'AC75f0880296f2c1377b2ca30442bbd3e1'
        auth_token = '01dfff8731923c8e91e47b469f533fd5'
        twilio_whatsapp_number = 'whatsapp:+14155238886'

        client = Client(account_sid, auth_token)

        verified_numbers = [
            '+918102637122',
            '+918109145639'
            #'+919111499689'
        ]

        message_text = " This message is sent from Mecaps SMS Dev Team."

        sent_messages = []

        for number in verified_numbers:
            try:
                message = client.messages.create(
                    from_=twilio_whatsapp_number,
                    body=message_text,
                    to=f'whatsapp:{number}'
                )
                sent_messages.append({
                    "to": number,
                    "sid": message.sid,
                    "status": "sent"
                })
            except Exception as e:
                sent_messages.append({
                    "to": number,
                    "error": str(e),
                    "status": "failed"
                })

        return Response({"results": sent_messages}, status=status.HTTP_200_OK)


class HolidayViewSet(ModelViewSet):
    queryset = Holiday.objects.all().order_by("-start_date")
    serializer_class = HolidaySerializer




class OfficeStaffAttendanceView(ModelViewSet):
    queryset = Attendance.objects.filter(
        office_staff__isnull=False,
        student__isnull=True,
        teacher__isnull=True
    )

    serializer_class = OfficeStaffAttendanceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        marked_at = validated_data["marked_at"]
        present_ids = validated_data.get("P", [])
        absent_ids = validated_data.get("A", [])
        leave_ids = validated_data.get("L", [])

        created_records = []

        for status_code, staff_ids in {
            "P": present_ids,
            "A": absent_ids,
            "L": leave_ids,
        }.items():

            for sid in staff_ids:
                attendance = Attendance.objects.create(
                    office_staff_id=sid,
                    status=status_code,
                    marked_at=marked_at
                )

                created_records.append(attendance)

        return Response(
            {
                "message": "Office staff attendance marked successfully.",
                "count": len(created_records)
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        instance = self.get_object()  # gets by pk

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True  # allows PATCH behavior
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Attendance deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )




class TeacherAttendanceView(ModelViewSet):
    queryset = Attendance.objects.filter(
        teacher__isnull=False,
        student__isnull=True,
        office_staff__isnull=True
    )
    serializer_class = TeacherAttendanceSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data

        marked_at = validated_data["marked_at"]
        present_ids = validated_data.get("P", [])
        absent_ids = validated_data.get("A", [])
        leave_ids = validated_data.get("L", [])

        created_records = []

        for status_code, teacher_ids in {
            "P": present_ids,
            "A": absent_ids,
            "L": leave_ids,
        }.items():

            for tid in teacher_ids:
                attendance = Attendance.objects.create(
                    teacher_id=tid,
                    status=status_code,
                    marked_at=marked_at
                )

                created_records.append(attendance)

        return Response(
            {
                "message": "Teacher attendance marked successfully.",
                "count": len(created_records)
            },
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, pk=None):
        instance = self.get_object()  # gets by pk

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=True  # allows PATCH behavior
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def destroy(self, request, pk=None):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Attendance deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )




