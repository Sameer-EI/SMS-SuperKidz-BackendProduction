from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets

from director.utils import send_email_notification

from .models import  *
from .serializers import *
from django.utils.dateformat import format as date_format
from datetime import date,datetime, timedelta
from django.db.models import Count, Q
from rest_framework.viewsets import ViewSet
from teacher.models import TeacherYearLevel
from student.models import Guardian,StudentGuardian, StudentYearLevel, Student
from django.shortcuts import get_object_or_404
import holidays
from director.views import send_whatsapp_message
from calendar import monthrange

#payload for MultipleAttendance
# {
#     "teacher": 1,
#     "year_level": 6,
#     "marked_at": "2025-09-24",
#     "P": [1],
#     "A": [104, 105],
#     "L": [106]
# }
class MultipleAttendanceViewSet1(ModelViewSet):
    queryset = StudentAttendance.objects.all()
    serializer_class = StudentAttendanceSerializer

    def create(self, request, *args, **kwargs):
        data = request.data

        # Validate marked_at
        try:
            marked_at_str = data.get("marked_at")
            marked_at = datetime.strptime(marked_at_str, "%Y-%m-%d").date() if marked_at_str else date.today()
            if marked_at > date.today():
                return Response({"error": "You cannot mark attendance for a future date."}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        # ========================= NEW:24/09/25 ==========================
         # Prevent attendance on Sundays
        if marked_at.weekday() == 6:
            return Response({"error": "Attendance cannot be marked on Sunday."}, status=status.HTTP_400_BAD_REQUEST)

         # Prevent attendance on school holidays
        if SchoolHoliday.objects.filter(date=marked_at).exists():
            return Response({"error": "Attendance cannot be marked on a school holiday."}, status=status.HTTP_400_BAD_REQUEST)

         # Prevent attendance on declared holidays
        if Holiday.objects.filter(start_date__lte=marked_at, end_date__gte=marked_at).exists():
            return Response({"error": "Attendance cannot be marked on a holiday."}, status=status.HTTP_400_BAD_REQUEST)
        # ==================================================================
        
        # Validate teacher
        teacher_id = data.get("teacher")
        if not teacher_id:
            return Response({"error": "teacher id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            teacher = Teacher.objects.get(id=teacher_id)
        except Teacher.DoesNotExist:
            return Response({"error": "Invalid teacher id."}, status=status.HTTP_404_NOT_FOUND)

        # Validate year level
        year_level_id = data.get("year_level")
        if not year_level_id:
            return Response({"error": "year level id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate presence of at least one status
        allowed_statuses = {'P', 'A', 'L'}
        all_student_ids = []
        status_provided = False

        for status_code in allowed_statuses:
            student_ids = data.get(status_code, [])
            if student_ids:
                if not isinstance(student_ids, list):
                    return Response({
                        "error": f"Value for status '{status_code}' must be a list of student IDs."
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Validate all IDs are integers
                for sid in student_ids:
                    if not isinstance(sid, int):
                        return Response({
                            "error": f"All student IDs under status '{status_code}' must be integers."
                        }, status=status.HTTP_400_BAD_REQUEST)

                status_provided = True
                all_student_ids.extend(student_ids)

        if not status_provided:
            return Response({
                "error": "At least one attendance status ('P', 'A', or 'L') with student IDs must be provided."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if attendance already exists
        already_marked_ids = StudentAttendance.objects.filter(
            student_id__in=all_student_ids,
            marked_at=marked_at
        ).values_list("student_id", flat=True)

        if already_marked_ids:
            return Response({
                "error": "Attendance already marked for this date.",
                "student_ids": list(already_marked_ids)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate student assignments
        invalid_students = []
        for sid in all_student_ids:
            try:
                student = Student.objects.get(id=sid)
            except Student.DoesNotExist:
                invalid_students.append(sid)
                continue

            if not student.student_year_levels.filter(level_id=year_level_id).exists():
                invalid_students.append(sid)

        if invalid_students:
            return Response({
                "error": "Some students are not assigned to the given year level or do not exist.",
                "student_ids": invalid_students
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create attendance records
        created_records = []
        absent_leave_students = []  # store absent or leave students for notification

        for status_code in allowed_statuses:
            for sid in data.get(status_code, []):
                student = Student.objects.get(id=sid)
                attendance = StudentAttendance.objects.create(
                    student=student,
                    status=status_code,
                    marked_at=marked_at,
                    teacher=teacher,
                    year_level_id=year_level_id
                )
                created_records.append(attendance)

                # Collect absent or leave for notification
                if status_code in ["A", "L"]:
                    absent_leave_students.append(student)

        # === Send Notifications for Absent / Leave Students ===
        for student in absent_leave_students:
            student_name = f"{student.user.first_name} {student.user.last_name}"
            
            # Get the guardian linked to this student
            try:
                student_guardian = StudentGuardian.objects.filter(student=student).first()
                guardian_user = student_guardian.guardian.user if student_guardian else None
            except StudentGuardian.DoesNotExist:
                guardian_user = None

            msg = (
                f"Dear Parent,\n\n"
                f"{student_name} was marked as Absent on {marked_at.strftime('%d-%m-%Y')}.\n"
                f"Kindly ensure regular attendance.\n\n"
                f"Regards,\nSchool Management"
            )

            # Send WhatsApp Message
            send_whatsapp_message(msg)

            # Send Email if guardian email exists
            if guardian_user and getattr(guardian_user, "email", None):
                send_email_notification(
                    to_email=guardian_user.email,
                    subject=f"Attendance Alert: {student_name} Absent on {marked_at.strftime('%d-%m-%Y')}",
                    message=msg
                )
        serializer = self.get_serializer(created_records, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class AttendanceReportViewSet(ReadOnlyModelViewSet):
    serializer_class = StudentAttendanceSerializer

    def get_queryset(self):
        queryset = StudentAttendance.objects.select_related('student', 'year_level')

        class_name = self.request.query_params.get('class')
        month = self.request.query_params.get('month')
        year = self.request.query_params.get('year')
        guardian_id = self.request.query_params.get('guardian_id')
        student_id = self.request.query_params.get('student_id')

        # Filter by guardian_id
        if guardian_id:
            student_ids = StudentGuardian.objects.filter(
                guardian_id=guardian_id
            ).values_list('student_id', flat=True)
            queryset = queryset.filter(student_id__in=student_ids)

        # Filter by student_id (overrides guardian filter if both given)
        if student_id:
            queryset = queryset.filter(student_id=student_id)

        # Filter by class name
        if class_name:
            queryset = queryset.filter(year_level__level_name__iexact=class_name)

        # Filter by month and year
        if month and year:
            try:
                month = int(month)
                year = int(year)
                queryset = queryset.filter(
                    marked_at__month=month,
                    marked_at__year=year
                )
            except ValueError:
                return StudentAttendance.objects.none()

        return queryset.order_by('student', 'marked_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        student_attendance_map = {}

        for record in queryset:
            student_id = record.student.id
            student_name = str(record.student)
            date_obj = record.marked_at
            # Format: 2/7/25 (Tuesday)
            date_str = date_format(date_obj, "j/n/y") + f" ({date_obj.strftime('%A')})"

            if student_id not in student_attendance_map:
                student_attendance_map[student_id] = {"Student name": student_name}

            student_attendance_map[student_id][date_str] = record.status

        final_data = list(student_attendance_map.values())
        return Response(final_data)

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
        total_students = Student.objects.count()
        present_today = StudentAttendance.objects.filter(marked_at=marked_date, status='P').count()
        overall_percentage = (present_today / total_students * 100) if total_students else 0

        # Step 3: Class-wise breakdown
        class_wise_data = []
        all_classes = YearLevel.objects.all()

        for cls in all_classes:
            attendances = StudentAttendance.objects.filter(marked_at=marked_date, year_level=cls)
            total = attendances.count()
            present = attendances.filter(status='P').count()
            percentage = (present / total * 100) if total else 0

            class_wise_data.append({
                "class_name": cls.level_name,
                "present": present,
                "total": total,
                "percentage": f"{percentage:.1f}%"
            })

        return Response({
            "date": marked_date.strftime("%Y-%m-%d"),
            "overall_attendance": {
                "present": present_today,
                "total": total_students,
                "percentage": f"{overall_percentage:.1f}%"
            },
            "class_wise_attendance": class_wise_data
        })

class TeacherAttendanceDashboard(ViewSet):
    def list(self, request):
        # Get month & year from query params (or use today's values)
        today = date.today()
        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))

        class_name = request.query_params.get("class_name")

        student_levels = StudentYearLevel.objects.all()

        if class_name:
            student_levels = student_levels.filter(level__level_name__iexact=class_name)

        result = []

        for syl in student_levels:
            attendance_qs = StudentAttendance.objects.filter(student=syl.student)

            # Monthly summary (filtered)
            monthly = attendance_qs.filter(marked_at__year=year, marked_at__month=month)
            m_present = monthly.filter(status='P').count()
            m_absent = monthly.filter(status='A').count()
            m_leave = monthly.filter(status='L').count()
            m_total = monthly.count()
            m_percentage = (m_present / m_total * 100) if m_total else 0.0

            # Yearly summary (filtered)
            yearly = attendance_qs.filter(marked_at__year=year)
            y_present = yearly.filter(status='P').count()
            y_absent = yearly.filter(status='A').count()
            y_leave = yearly.filter(status='L').count()
            y_total = yearly.count()
            y_percentage = (y_present / y_total * 100) if y_total else 0.0

            result.append({
                "student_name": f"{syl.student.user.first_name} {syl.student.user.last_name}",
                "class_name": syl.level.level_name,
                "filter_month": month,
                "filter_year": year,
                "monthly_percentage": round(m_percentage, 1),
                "yearly_percentage": round(y_percentage, 1),
                "monthly_summary": {
                    "present": m_present,
                    "absent": m_absent,
                    "leave": m_leave,
                    "total_days": m_total
                },
                "yearly_summary": {
                    "present": y_present,
                    "absent": y_absent,
                    "leave": y_leave,
                    "total_days": y_total
                }
            })

        return Response(result)


class StudentOwnAttendanceViewSet(ViewSet):
    def retrieve(self, request, pk=None):
        today = date.today()
        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))

        # Get student by ID
        student = get_object_or_404(Student, id=pk)

        # Get all attendance records
        attendance_qs = StudentAttendance.objects.filter(student=student)

        # Get latest year_level from attendance
        latest_attendance = attendance_qs.order_by('-marked_at').first()
        year_level_name = (
            latest_attendance.year_level.level_name
            if latest_attendance and latest_attendance.year_level
            else "N/A"
        )

        # Monthly summary
        monthly = attendance_qs.filter(marked_at__year=year, marked_at__month=month)
        m_present = monthly.filter(status='P').count()
        m_absent = monthly.filter(status='A').count()
        m_leave = monthly.filter(status='L').count()
        m_total = monthly.count()
        m_percentage = (m_present / m_total * 100) if m_total else 0.0

        # Yearly summary
        yearly = attendance_qs.filter(marked_at__year=year)
        y_present = yearly.filter(status='P').count()
        y_absent = yearly.filter(status='A').count()
        y_leave = yearly.filter(status='L').count()
        y_total = yearly.count()
        y_percentage = (y_present / y_total * 100) if y_total else 0.0

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
                "total_days": m_total
            },
            "yearly_summary": {
                "present": y_present,
                "absent": y_absent,
                "leave": y_leave,
                "total_days": y_total
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
        month = int(request.query_params.get("month", today.month))
        year = int(request.query_params.get("year", today.year))

        student_links = StudentGuardian.objects.filter(guardian=guardian)
        children = [link.student for link in student_links]

        response_data = []

        for student in children:
            try:
                year_level = StudentYearLevel.objects.get(student=student)
            except StudentYearLevel.DoesNotExist:
                continue

            # Monthly
            monthly_qs = StudentAttendance.objects.filter(
                student=student,
                marked_at__year=year,
                marked_at__month=month
            )
            m_total = monthly_qs.count()
            m_present = monthly_qs.filter(status='P').count()
            m_absent = monthly_qs.filter(status='A').count()
            m_leave = monthly_qs.filter(status='L').count()
            m_percent = round((m_present / m_total) * 100, 1) if m_total else 0.0

            # Yearly
            yearly_qs = StudentAttendance.objects.filter(
                student=student,
                marked_at__year=year
            )
            y_total = yearly_qs.count()
            y_present = yearly_qs.filter(status='P').count()
            y_absent = yearly_qs.filter(status='A').count()
            y_leave = yearly_qs.filter(status='L').count()
            y_percent = round((y_present / y_total) * 100, 1) if y_total else 0.0

            response_data.append({
                'student_name': f"{student.user.first_name} {student.user.last_name}",
                'class_name': year_level.level.level_name,
                'monthly_summary': {
                    "month": month,
                    "present": m_present,
                    "absent": m_absent,
                    "leave": m_leave,
                    "total_days": m_total,
                    "percentage": f"{m_percent}%"
                },
                'yearly_summary': {
                    "year": year,
                    "present": y_present,
                    "absent": y_absent,
                    "leave": y_leave,
                    "total_days": y_total,
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
   
    
    
class TeacherYearLevelList(APIView):
    def get(self, request, teacher_id):
        levels = TeacherYearLevel.objects.filter(teacher_id=teacher_id).select_related('year_level')
        data = [
            {
                "teacher_year_level_id": l.id,  # This is the ID of the relation record
                "year_level_id": l.year_level.id,
                "year_level_name": str(l.year_level)
            }
            for l in levels
        ]
        return Response(data)

        #------------- was creating numerous entries-------24/09/25--------------


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

'''
office staff attendance payload formats:

single:
  {"Office_staff": 5,
  "date": "2025-11-12",
  "status": "Present"}

multiple:

  [
  {"office_staff_id": 1, "status": "Present", "date": "2025-11-12"},
  {"office_staff_id": 2, "status": "Absent", "date": "2025-11-12"}
  ]


'''

class OfficeStaffAttendanceView(ModelViewSet):
    queryset = OfficeStaffAttendance.objects.all().order_by("-date")
    serializer_class = OfficeStaffAttendanceSerializer

    def create(self, request, *args, **kwargs):
        data = request.data

        # Handle both single and multiple records
        if isinstance(data, dict):
            records = [data]
        elif isinstance(data, list):
            records = data
        else:
            return Response(
                {"error": "Invalid input format. Must be dict or list."},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = []
        errors = []

        for record in records:
            office_staff_id = record.get("office_staff_id")
            status_input = record.get("status")
            date_str = record.get("date", str(date.today()))

            # Missing required fields
            if not office_staff_id or not status_input:
                errors.append({"error": "office_staff_id and status are required", "data": record})
                continue

            # Validate date format
            try:
                attendance_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                errors.append({"error": f"Invalid date format: {date_str}"})
                continue

            staff = OfficeStaff.objects.get(id=office_staff_id)
            staff_name = staff.user.get_full_name()

            # Future date check
            if attendance_date > date.today():
                errors.append({"error": f"Cannot mark attendance for a future date for {staff_name} on {attendance_date}.", "office_staff_id": office_staff_id})
                continue

            # Sunday check
            if attendance_date.weekday() == 6:
                errors.append({"error": f"Cannot mark attendance on Sunday for {staff_name} on {attendance_date}.", "office_staff_id": office_staff_id})
                continue

            # Holiday checks
            if SchoolHoliday.objects.filter(date=attendance_date).exists():
                errors.append({"error": f"Cannot mark attendance on a school holiday for {staff_name} on {attendance_date}.", "office_staff_id": office_staff_id})
                continue

            if Holiday.objects.filter(start_date__lte=attendance_date, end_date__gte=attendance_date).exists():
                errors.append({"error": f"Cannot mark attendance on a holiday for {staff_name} on {attendance_date}.", "office_staff_id": office_staff_id})
                continue

            # Only within the last 7 days
            seven_days_ago = date.today() - timedelta(days=7)
            if attendance_date < seven_days_ago:
                errors.append({
                    "error": f"You can only mark attendance for the last 7 days for {staff_name}.",
                    "office_staff_id": office_staff_id
                })
                continue

            # Staff existence check
            try:
                staff = OfficeStaff.objects.get(id=office_staff_id)
            except OfficeStaff.DoesNotExist:
                errors.append({"error": f"Office staff not found (ID: {office_staff_id})"})
                continue

            # Duplicate attendance check
            if OfficeStaffAttendance.objects.filter(office_staff=staff, date=attendance_date).exists():
                errors.append({
                    "message": f"Attendance already marked for {staff_name} on {attendance_date}.",
                    "office_staff_id": office_staff_id,
                    "date": str(attendance_date)
                })
                continue

            # Create record
            OfficeStaffAttendance.objects.create(
                office_staff=staff,
                date=attendance_date,
                status=status_input
            )

            results.append({
                "message": f"Attendance marked successfully for {staff_name}",
                "office_staff_id": office_staff_id,
                "status": status_input,
                "date": str(attendance_date)
            })

        # Final response
        response_data = {
            "success_count": len(results),
            "error_count": len(errors),
            "details": {
                "marked": results,
                "skipped": errors
            }
        }

        return Response(
            response_data,
            status=status.HTTP_200_OK if results else status.HTTP_400_BAD_REQUEST
        )
