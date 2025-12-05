from django.forms import DateField, ValidationError
import requests
from requests.auth import HTTPBasicAuth
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count
from collections import OrderedDict
from attendance.models import StudentAttendance
from director.permission import *
from director.utils import calculate_subject_summary
from rest_framework.exceptions import ValidationError
from director.permission import IsDirectororOfficeStaff, IsDirector, RoleBasedExamPermission, RoleBasedPermission

from .serializers import *
from rest_framework import filters
from .models import *
from rest_framework .views import APIView       # As of 07May25 at 12:30 PM
# from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Sum
from rest_framework.decorators import action
from django.utils.dateparse import parse_date

from rest_framework.exceptions import PermissionDenied
from django.db.models.functions import Coalesce
from django.db.models import Sum, DecimalField
# views.py

from django.db.models import Count, F, ExpressionWrapper, IntegerField ,Func , Value
# from razorpay.errors import SignatureVerificationError, InvalidOperation # as of 04Oct25
from razorpay.errors import SignatureVerificationError
from decimal import Decimal, InvalidOperation 

import razorpay
from django.conf import settings
from django.shortcuts import get_object_or_404
from datetime import datetime
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets, status
import json  #  This goes at the top of the file
from django.db.models import Q
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models.functions import Cast
from teacher.models import Teacher, TeacherYearLevel



from django.db.models import OuterRef, Subquery, Sum, Value, FloatField


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

import random
import string
from django.db.models import Sum, F, Value, DecimalField
from django.db.models.functions import Coalesce
from django.db.models import Q
from django.db.models import Q, Sum, Value, FloatField
from django.db.models.fields import DateField  # This avoids shadowing
from decimal import Decimal, InvalidOperation # added as of 04Oct25
from razorpay.errors import SignatureVerificationError  # added as of 04Oct25
from rest_framework import status as drf_status
from decimal import ROUND_HALF_UP





client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# ---------------------------------------------------------------------------------------------------------------------------------------------         

#    Document fetch dashboard

@api_view(["GET"])
def document_fetch_dashboard(request):
    user_type = request.query_params.get('user_type')        # student, teacher, etc.
    uploaded = request.query_params.get('uploaded')          # true / false
    class_id = request.query_params.get('class')             # e.g., 1, 2 (level_id)

    data = []

    def format_entry(instance, type_label, has_doc, class_label):
        return {
            "user_type": type_label,
            "name": f"{instance.user.first_name} {instance.user.last_name}",
            "has_uploaded_document": has_doc,
            "class": class_label
        }

    def get_class(instance, label):
        if label == "student":
            return StudentYearLevel.objects.filter(student=instance).select_related("level").first()
        elif label == "teacher":
            return TeacherYearLevel.objects.filter(teacher=instance).select_related("year_level").first()
        elif label == "guardian":
            student_guardian = StudentGuardian.objects.filter(guardian=instance).select_related("student").first()
            if student_guardian:
                student = student_guardian.student
                return StudentYearLevel.objects.filter(student=student).select_related("level").first()
            return None
        elif label == "office_staff":
            return None
        else:
            return None

    def process_queryset(queryset, label, doc_field):
        for instance in queryset:
            has_doc = Document.objects.filter(**{doc_field: instance}).exists()

            # Uploaded filter
            if uploaded == "true" and not has_doc:
                continue
            if uploaded == "false" and has_doc:
                continue

            class_obj = get_class(instance, label)
            if class_obj:
                level_id = class_obj.level.id if label in ["student", "guardian"] else class_obj.year_level.id
                level_name = class_obj.level.level_name if label in ["student", "guardian"] else class_obj.year_level.level_name
            else:
                level_id = None
                level_name = "N/A" if label == "office_staff" else "Unknown"

            # Class ID filter
            if class_id and str(level_id) != class_id:
                continue

            data.append(format_entry(instance, label, has_doc, level_name))

    # Main filtering logic
    if user_type == "student" or user_type is None:
        process_queryset(Student.objects.all(), "student", "student")

    if user_type == "teacher" or user_type is None:
        process_queryset(Teacher.objects.all(), "teacher", "teacher")

    if user_type == "guardian" or user_type is None:
        process_queryset(Guardian.objects.all(), "guardian", "guardian")

    if user_type == "office_staff" or user_type is None:
        process_queryset(OfficeStaff.objects.all(), "office_staff", "office_staff")

    if user_type not in ["student", "teacher", "guardian", "office_staff", None]:
        return Response({"error": "Invalid user_type"}, status=status.HTTP_400_BAD_REQUEST)

    return Response(data)




# user_type=student|teacher|guardian|office_staff

# uploaded=true|false

# class=Nursery|KG|Class 1|





#  ____________________________________________________________ class period view  ____________________________________________________________

@api_view(['GET'])
def assigned_periods(request):
    year_level_id = request.query_params.get("year_level_id")

    if not year_level_id:
        return Response({"error": "year_level_id query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        year_level = YearLevel.objects.get(id=year_level_id)
    except YearLevel.DoesNotExist:
        return Response({"error": "YearLevel not found"}, status=status.HTTP_404_NOT_FOUND)

    class_periods = ClassPeriod.objects.filter(year_level=year_level)

    assigned_periods = []
    for period in class_periods:
        assigned_periods.append({
            "subject": str(period.subject),
            "teacher": str(period.teacher),
            "start_time": period.start_time.start_period_time.strftime('%I:%M %p'),
            "end_time": period.end_time.end_period_time.strftime('%I:%M %p'),
        })

    return Response({
        "class": year_level.level_name,
        "total_periods": class_periods.count(),
        "assigned_periods": assigned_periods
    })
# from django.db.models import Q
# from rest_framework.decorators import api_view
# from rest_framework.response import Response
# from rest_framework import status

# @api_view(['GET'])
# def assigned_periods(request):
#     year_level_id = request.query_params.get("year_level_id")

#     if not year_level_id:
#         return Response({"error": "year_level_id is required"}, status=status.HTTP_400_BAD_REQUEST)

#     try:
#         year_level = YearLevel.objects.get(id=year_level_id)
#     except YearLevel.DoesNotExist:
#         return Response({"error": "YearLevel not found"}, status=status.HTTP_404_NOT_FOUND)

#     class_periods = ClassPeriod.objects.filter(year_level=year_level)
#     assigned_periods = []

#     for period in class_periods:
#         # Check if the teacher is already assigned to another class at the same time
#         teacher_conflicts = ClassPeriod.objects.filter(
#             Q(teacher=period.teacher) &
#             Q(start_time=period.start_time) &
#             Q(end_time=period.end_time) &
#             ~Q(year_level=year_level)  # Exclude current class
#         )

#         if teacher_conflicts.exists():
#             conflict = teacher_conflicts.first()
#             return Response({
#                 "error": f"Teacher {period.teacher} is already teaching {conflict.subject} in {conflict.year_level.level_name} at this time."
#             }, status=status.HTTP_400_BAD_REQUEST)

#         assigned_periods.append({
#             "subject": str(period.subject),
#             "teacher": str(period.teacher),
#             "start_time": period.start_time.start_period_time.strftime('%I:%M %p'),
#             "end_time": period.end_time.end_period_time.strftime('%I:%M %p'),
#             "classroom": str(period.classroom),
#             "term": period.term,
#             "name": period.name
#         })

#     return Response({
#         "class": year_level.level_name,
#         "total_periods": class_periods.count(),
#         "assigned_periods": assigned_periods
#     })
#   ---------------------------------------------  Director Dashboard view   ----------------------------------------------------------



@api_view(["GET"])
def Director_Dashboard_Summary(request):
    current_date = datetime.now().date()

    # Get current SchoolYear (academic year)
    current_school_year = (
        SchoolYear.objects
        .filter(start_date__lte=current_date, end_date__gte=current_date)
        .order_by('-start_date')
        .first()
    )

    # if current_school_year:
    #     new_admissions_count = Admission.objects.filter(
    #         admission_date__gte=current_school_year.start_date,
    #         admission_date__lte=current_school_year.end_date
    #     ).count()
    # else:
    #     new_admissions_count = 0
    if current_school_year:
        new_admissions_count = Admission.objects.filter(school_year=current_school_year).count()
    else:
        new_admissions_count = 0

    summary = {
        "new_admissions": new_admissions_count,
        "students": Student.objects.count(),
        "teachers": Teacher.objects.count()
    }

    student_total = summary["students"]
    teacher_total = summary["teachers"]

    # Gender count
    student_male = Student.objects.filter(gender__iexact="Male").count()
    student_female = Student.objects.filter(gender__iexact="Female").count()

    teacher_male = Teacher.objects.filter(gender__iexact="Male").count()
    teacher_female = Teacher.objects.filter(gender__iexact="Female").count()

    def get_percentage(count, total):
        return round((count / total) * 100, 2) if total else 0

    gender_distribution = {
        "students": {
            "count": {
                "male": student_male,
                "female": student_female
            },
            "percentage": {
                "male": get_percentage(student_male, student_total),
                "female": get_percentage(student_female, student_total)
            },
        },
        "teachers": {
            "count": {
                "male": teacher_male,
                "female": teacher_female
            },
            "percentage": {
                "male": get_percentage(teacher_male, teacher_total),
                "female": get_percentage(teacher_female, teacher_total)
            },
        }
    }

    # Class-wise strength
    class_data = StudentYearLevel.objects.values("level__level_name").annotate(total=Count("student"))
    class_strength = {entry["level__level_name"]: entry["total"] for entry in class_data}

    # Academic Year-wise strength
    school_years = SchoolYear.objects.order_by("start_date")
    students_per_year = OrderedDict()

    for year in school_years:
        year_range = f"{year.start_date.year}-{year.end_date.year}"
        count = StudentYearLevel.objects.filter(year=year).count()
        students_per_year[year_range] = count

    return Response({
        "summary": summary,
        "gender_distribution": gender_distribution,
        "class_strength": class_strength,
        "students_per_year": students_per_year
    })



# ---------------------------------------------------------   Teacher Dashboard View  ----------------------------------------------------------
 


@api_view(["GET"])
def teacher_dashboard(request, id):
    try:
        teacher = Teacher.objects.get(user_id=id)
        teacher_name = f"{teacher.user.first_name} {teacher.user.last_name}"

       
        assigned_levels = TeacherYearLevel.objects.filter(teacher=teacher).select_related("year_level")

        class_summary = []

        for assigned in assigned_levels:
            level = assigned.year_level
            level_name = level.level_name

            total_students = StudentYearLevel.objects.filter(level=level).count()

            class_period = ClassPeriod.objects.filter(
                teacher=teacher,
                classroom__isnull=False
            ).select_related("classroom").first()

            room_name = class_period.classroom.room_name if class_period and class_period.classroom else None

            class_summary.append({
                "level_name": level_name,
                "total_students": total_students,
                "room_name": room_name
            })

        return Response({
            "teacher_name": teacher_name,
            "total_assigned_classes": len(class_summary),
            "class_summary": class_summary
        })

    except Teacher.DoesNotExist:
        return Response({"error": "Teacher not found"}, status=404)


# --------------------------------------------------------- Guardian Dashboard View  ----------------------------------------------------------
@api_view(["GET"])
def guardian_dashboard(request, id=None):
    if not id:
        return Response({"error": "Guardian ID is required"}, status=400)

    try:
        guardian = Guardian.objects.get(user_id=id)  # Corrected line
    except Guardian.DoesNotExist:
        return Response({"error": "Guardian not found"}, status=404)

    student_links = StudentGuardian.objects.filter(guardian=guardian)
    children_data = []

    for link in student_links:
        student = link.student

        # Latest class info (YearLevel + SchoolYear)
        year_level_info = StudentYearLevel.objects.filter(student=student).last()

        children_data.append({
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "class": f"{year_level_info.level.level_name} ({year_level_info.year.year_name})"
            if year_level_info else "Not Assigned"
        })

    return Response({
        "guardian": f"{guardian.user.first_name} {guardian.user.last_name}",
        "total_children": student_links.count(),
        "children": children_data
    })
#  ----------------------------------------------------------------- Student Dashboard View --------------------------------------------------
# @api_view(["GET"])
# def student_dashboard(request, id=None):
#     if not id:
#         return Response({"error": "Student ID is required"}, status=400)

#     try:
#         student = Student.objects.get(user__id=id)
#     except Student.DoesNotExist:
#         return Response({"error": "Student not found"}, status=404)

#     # Get optional year_level_id from query params
#     year_level_id = request.query_params.get("year_level_id")

#     # Filter year level info
#     year_level_info = None
#     if year_level_id:
#         year_level_info = StudentYearLevel.objects.filter(student=student, level_id=year_level_id).last()
#     else:
#         year_level_info = StudentYearLevel.objects.filter(student=student).last()

#     # Guardian details
#     guardian_links = StudentGuardian.objects.filter(student=student)
#     guardians_data = []

#     for link in guardian_links:
#         guardian = link.guardian
#         guardians_data.append({
#             "guardian_name": f"{guardian.user.first_name} {guardian.user.last_name}"
#         })

#     # Child info output
#     children_data = []

#     if year_level_info:
#         children_data.append({
#             "student_name": f"{student.user.first_name} {student.user.last_name}",
#             "class": f"{year_level_info.level.level_name} ({year_level_info.year.year_name})",
#             "year_level_id": year_level_info.level.id
#         })
#     else:
#         children_data.append({
#             "student_name": f"{student.user.first_name} {student.user.last_name}",
#             "class": "Not Assigned",
#             "year_level_id": None
#         })

#     return Response({
#         "guardian": guardians_data,
#         "total_children": 1,
#         "children": children_data
#     })


@api_view(["GET"])
def student_dashboard(request, id=None):
    if not id:
        return Response({"error": "Student ID is required"}, status=400)

    try:
        student = Student.objects.get(user_id=id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    # Get optional year_level_id from query params
    year_level_id = request.query_params.get("year_level_id")

    # Filter year level info
    year_level_info = None
    if year_level_id:
        year_level_info = StudentYearLevel.objects.filter(student=student, level_id=year_level_id).last()
    else:
        year_level_info = StudentYearLevel.objects.filter(student=student).last()

    # Guardian details
    guardian_links = StudentGuardian.objects.filter(student=student)
    guardians_data = []

    for link in guardian_links:
        guardian = link.guardian
        guardians_data.append({
            "guardian_name": f"{guardian.user.first_name} {guardian.user.last_name}"
        })

    # Child info output
    children_data = []

    if year_level_info:
        children_data.append({
            "student_id": student.id,  # Added student ID here
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "class": f"{year_level_info.level.level_name} ({year_level_info.year.year_name})",
            "year_level_id": year_level_info.level.id
        })
    else:
        children_data.append({
            "student_id": student.id,  # Added student ID here
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "class": "Not Assigned",
            "year_level_id": None
        })

    return Response({
        "guardian": guardians_data,
        "total_children": 1,
        "children": children_data
    })
# --------------------------------------------------------- office Staff Dashboard View  ----------------------------------------------------------



@api_view(["GET"])
def office_staff_dashboard(request):
    staff = OfficeStaff.objects.first()
    if not staff or not staff.user:
        return Response({"error": "No office staff found"}, status=404)

    current_date = datetime.now().date()

    current_year = (
        SchoolYear.objects
        .filter(start_date__lte=current_date, end_date__gte=current_date)
        .order_by('-start_date')
        .first()
    )

    if not current_year:
        return Response({"error": "Current academic year not found"}, status=404)

    # Academic Year-wise Admissions & Students
    school_years = SchoolYear.objects.order_by("start_date")
    admissions_trend = OrderedDict()
    students_per_year = OrderedDict()

    for year in school_years:
        year_range = f"{year.start_date.year}-{year.end_date.year}"

        # Admissions in that academic year
        # admissions_count = Admission.objects.filter(
        #     admission_date__gte=year.start_date,
        #     admission_date__lte=year.end_date
        # ).count()
        # New logic (based on ForeignKey)
        admissions_count = Admission.objects.filter(school_year=year).count()

        admissions_trend[year_range] = admissions_count

        # Students enrolled in that academic year
        students_count = StudentYearLevel.objects.filter(year=year).count()
        students_per_year[year_range] = students_count

    # Current year admissions
    new_admissions = admissions_trend.get(
        f"{current_year.start_date.year}-{current_year.end_date.year}", 0
    )

    total_admissions = sum(admissions_trend.values())

    return Response({
        # "staff_name": f"{staff.user.first_name} {staff.user.last_name}",
        "current_academic_year": f"{current_year.start_date.year}-{current_year.end_date.year}",
        "new_admissions_this_year": new_admissions,
        "admissions_per_year": admissions_trend,
        "total_admissions": total_admissions,
        "students_per_year": students_per_year
    })





# --------------------------------------------------------- student dashboard View  ----------------------------------------------------------





# @api_view(["GET"])
# def student_dashboard(request, id):
#     try:
#         student = Student.objects.get(id=id)
#     except Student.DoesNotExist:
#         return Response({"error": "Student not found"}, status=404)

#     # Get the latest admission if multiple exist
#     admission = Admission.objects.filter(student=student).order_by('-admission_date').first()
#     if not admission:
#         return Response({"error": "Admission record not found"}, status=404)

#     # Total Fee from YearLevelFee
#     year_level_fees = YearLevelFee.objects.filter(year_level=admission.year_level)
#     total_fee = year_level_fees.aggregate(total=Sum('amount'))['total'] or 0

#     # Paid Amount from FeeRecord
#     paid_amount = FeeRecord.objects.filter(student=student).aggregate(paid=Sum('paid_amount'))['paid'] or 0

#     due_amount = total_fee - paid_amount

#     return Response({
#         "student_name": student.user.get_full_name(),
#         "year_level": str(admission.year_level),
#         "total_fee": float(total_fee),
#         "paid_fee": float(paid_amount),
#         "due_fee": float(due_amount)
#     })


# -------------------------------------------------  Fees summary view  ----------------------------------------------------------

# @api_view(["GET"])
# def director_fee_summary(request):
#     month = request.GET.get("month")  
#     year = request.GET.get("year")    

#     # School-level summary
#     total_students = Student.objects.count()

#     fee_qs = FeeRecord.objects.all()

#     if month and year:
#         fee_qs = fee_qs.filter(month=month, payment_date__year=year)
#     elif year:
#         fee_qs = fee_qs.filter(payment_date__year=year)

#     total_fee = fee_qs.aggregate(
#         total=Coalesce(Sum('total_amount', output_field=DecimalField()), Decimal("0.00"))
#     )['total']

#     total_paid = fee_qs.aggregate(
#         paid=Coalesce(Sum('paid_amount', output_field=DecimalField()), Decimal("0.00"))
#     )['paid']

#     total_due = fee_qs.aggregate(
#         due=Coalesce(Sum('due_amount', output_field=DecimalField()), Decimal("0.00"))
#     )['due']

#     # Class-wise summary
#     class_data = []
#     all_class_periods = ClassPeriod.objects.select_related('classroom__room_type').all()

#     for period in all_class_periods:
#         students_in_class = Student.objects.filter(classes=period).distinct()
#         student_ids = students_in_class.values_list('id', flat=True)

#         class_fee_qs = FeeRecord.objects.filter(student_id__in=student_ids)
#         if month and year:
#             class_fee_qs = class_fee_qs.filter(month=month, payment_date__year=year)

#         class_total_fee = class_fee_qs.aggregate(
#             total=Coalesce(Sum('total_amount', output_field=DecimalField()), Decimal("0.00"))
#         )['total']

#         class_total_paid = class_fee_qs.aggregate(
#             paid=Coalesce(Sum('paid_amount', output_field=DecimalField()), Decimal("0.00"))
#         )['paid']

#         class_total_due = class_fee_qs.aggregate(
#             due=Coalesce(Sum('due_amount', output_field=DecimalField()), Decimal("0.00"))
#         )['due']

#         class_data.append({
#             "class_name": f"{period.classroom.room_type} - {period.classroom.room_name}",
#             "total_students": students_in_class.count(),
#             "total_fee": class_total_fee,
#             "paid_fee": class_total_paid,
#             "due_fee": class_total_due
#         })

#     data = {
#         "school_summary": {
#             "total_students": total_students,
#             "total_fee": total_fee,
#             "paid_fee": total_paid,
#             "due_fee": total_due,
#         },
#         "class_summary": class_data
#     }

#     return Response(data)


# -------------------------------------------------  Guardian income distribution view  ----------------------------------------------------------





@api_view(["GET"])
def guardian_income_distribution(request):
    bucket_size = int(request.GET.get("bucket_size", 10000)) 
    max_income = int(request.GET.get("max_income", 200000))   

    income_bucket_expr = ExpressionWrapper(
        Func(
            F('annual_income') / Value(bucket_size),
            function='FLOOR'
        ),
        output_field=IntegerField()
    )

    data = (
        Guardian.objects
        .filter(annual_income__lt=max_income)
        .annotate(income_bucket=income_bucket_expr)
        .values('income_bucket')
        .annotate(count=Count('id'))
        .order_by('income_bucket')
    )

    result = []
    for row in data:
        start = row['income_bucket'] * bucket_size
        end = start + bucket_size
        result.append({
            "range": f"₹{start} - ₹{end}",
            "count": row["count"]
        })

    return Response(result)


# ------------------------------------------------------------------------  livelihood  distribution view  ----------------------------------------------------------


@api_view(["GET"])
def livelihood_distribution(request):
    govt_count = Guardian.objects.filter(means_of_livelihood='Govt').count()
    non_govt_count = Guardian.objects.filter(means_of_livelihood='Non-Govt').count()

    return Response([
        {"category": "Government", "count": govt_count},
        {"category": "Non-Government", "count": non_govt_count}
    ])



#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

### ----------------------------- Category Count Dashboard API ----------------- ###
### ------------------- As of 25June25 at 12:35 --------------- ###

@api_view(["GET"])
def student_category(request):
    category_counts = Student.objects.values('category').annotate(total=Count('id'))
    total_students = Student.objects.count()

    # Map category codes to their display names
    category_display_map = dict(Student._meta.get_field('category').choices or [])

    result = [
        {
            # "category_code": item["category"],  # Uncomment if needed
            "category_name": category_display_map.get(item["category"], "Unknown"),
            "count": item["total"],
            "percentage": round((item["total"] / total_students) * 100, 2) if total_students > 0 else 0.0
        }
        for item in category_counts
    ]

    return Response(result, status=status.HTTP_200_OK)

### -------------------------------------------------------------- ###

### ----------------------------- Income Distribution Dashboard API ----------------- ###
### ------------------- As of 25June25 at 12:35 --------------- ###

@api_view(["GET"])
def guardian_income_distribution(request):
    # Define updated income brackets
    brackets = {
        "Below 1 Lakh": (0, 100000),
        "1 – 3 Lakhs": (100001, 300000),
        "3 – 5 Lakhs": (300001, 500000),
        "5 – 8 Lakhs": (500001, 800000),
        "8 – 10 Lakhs": (800001, 1000000),
        "Above 10 Lakhs": (1000001, None),
    }

    total_guardians = Guardian.objects.exclude(annual_income__isnull=True).count()

    results = []

    for label, (min_income, max_income) in brackets.items():
        if max_income is not None:
            count = Guardian.objects.filter(
                annual_income__gte=min_income,
                annual_income__lte=max_income
            ).count()
        else:
            count = Guardian.objects.filter(
                annual_income__gte=min_income
            ).count()

        percentage = round((count / total_guardians) * 100, 2) if total_guardians > 0 else 0.0

        results.append({
            "income_range": label,
            "count": count,
            "percentage": percentage
        })

    return Response(results, status=status.HTTP_200_OK)
### -------------------------------------------------------------- ###


### ------------------- As of 25June25 at 12:35 --------------- ###
### ---- complete fee dashboard ------- ###

# @api_view(["GET"])
# def fee_dashboard(request):
#     filter_month = request.query_params.get("month")
#     qs = FeeRecord.objects.all()

#     # -------- Overall Summary --------
#     total = qs.aggregate(
#         total=Coalesce(Sum(F("total_amount") + F("late_fee"), output_field=FloatField()), Value(0.0))
#     )["total"]
#     paid = qs.aggregate(
#         paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0))
#     )["paid"]
#     late_fee = qs.aggregate(
#         late=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0))
#     )["late"]

#     due = max(0, total - paid)
#     paid_percent = round((paid / total) * 100, 2) if total > 0 else 0.0
#     due_percent = round((due / total) * 100, 2) if total > 0 else 0.0
#     total_percent = round(paid_percent + due_percent, 2)

#     overall_summary = {
#         "total_amount": round(total, 2),
#         "paid_amount": round(paid, 2),
#         "due_amount": round(due, 2),
#         "late_fee": round(late_fee, 2),
#         "paid_percent": paid_percent,
#         "due_percent": due_percent,
#         "total_percent": total_percent
#     }

#     # -------- Monthly Summary --------
#     # https://187gwsw1-7000.inc1.devtunnels.ms/d/fee-dashboard/?month=June
#     monthly_qs = qs.filter(month__iexact=filter_month) if filter_month else qs
#     monthly_data = (
#         monthly_qs.values("month")
#         .annotate(
#             total_base=Coalesce(Sum("total_amount", output_field=FloatField()), Value(0.0)),
#             late_fee=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0)),
#             paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
#         )
#         .order_by("month")
#     )

#     monthly_summary = []
#     for item in monthly_data:
#         total = item["total_base"] + item["late_fee"]
#         due = max(0, total - item["paid"])
#         monthly_summary.append({
#             "month": item["month"],
#             "total_amount": round(total, 2),
#             "paid_amount": round(item["paid"], 2),
#             "due_amount": round(due, 2),
#             "late_fee": round(item["late_fee"], 2),
#             "paid_percent": round((item["paid"] / total) * 100, 2) if total > 0 else 0.0,
#             "due_percent": round((due / total) * 100, 2) if total > 0 else 0.0,
#             "late_fee_percent": round((item["late_fee"] / total) * 100, 2) if total > 0 else 0.0,
#             "total_percent": 100.0
#         })

#     # -------- Payment Mode Distribution --------
#     payment_data = FeeRecord.objects.values("payment_mode").annotate(count=Count("id"))
#     total_payments = sum(item["count"] for item in payment_data)

#     payment_distribution = [
#         {
#             "payment_mode": item["payment_mode"],
#             "count": item["count"],
#             "percentage": round((item["count"] / total_payments) * 100, 2) if total_payments else 0.0
#         } for item in payment_data
#     ]

#     # -------- Top Defaulters (No Payment in Last 3 Months) --------

#     # Defaulter Summary (based on dues in the last 3 months)
#     three_months_ago = datetime.now().date() - timedelta(days=90)

#     due_per_month = FeeRecord.objects.filter(
#         payment_date__lt=three_months_ago
#     ).values("student_id").annotate(
#         total=Coalesce(Sum(F("total_amount") + F("late_fee"), output_field=FloatField()), Value(0.0)),
#         paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
#     ).annotate(
#         due=F("total") - F("paid")
#     ).filter(due__gt=0)

#     defaulter_count = due_per_month.count()
#     total_students = Student.objects.count()
#     defaulter_percent = round((defaulter_count / total_students) * 100, 2) if total_students > 0 else 0.0
    
    
#     # --------- Fee Defaulters (Based on Due Older Than 3 Months) ---------
#     # three_months_ago = now().date() - timedelta(days=90)

#     # # Get only FeeRecords from the last 3 months
#     # recent_dues_qs = FeeRecord.objects.filter(payment_date__gte=three_months_ago)

#     # # Annotate due per record
#     # recent_dues_qs = recent_dues_qs.annotate(
#     #     total_due=F('total_amount') + F('late_fee') - F('paid_amount')
#     # ).filter(total_due__gt=0)

#     # # Total number of fee records with due in last 3 months
#     # defaulter_count = recent_dues_qs.values('student').distinct().count()

#     # # Total number of students overall
#     # total_students = Student.objects.count()

#     # defaulter_percent = round((defaulter_count / total_students) * 100, 2) if total_students > 0 else 0.0

#     # -------- Response --------
#     return Response({
#     "overall_summary": overall_summary,
#     "monthly_summary": monthly_summary,
#     "payment_mode_distribution": payment_distribution,
#     "defaulter_summary": {
#         "count": defaulter_count,
#         "percent": defaulter_percent,
#     }
# })




@api_view(["GET", "POST", "PUT", "DELETE"])
def YearLevelView(request, id=None):
    if request.method == "GET":
        if id is not None:
            try:
                YearLevels = YearLevel.objects.get(pk=id)
                serialize = YearLevelSerializer(YearLevels, many=False)
                return Response(serialize.data, status=status.HTTP_200_OK)
            except YearLevel.DoesNotExist:
                return Response(
                    data={"message": "Data Not Found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            except Exception as e:
                return Response(
                    data={"message": f"something went wrong {e}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            YearLevels = YearLevel.objects.all()
            serialized = YearLevelSerializer(YearLevels, many=True)
            return Response(serialized.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        data = request.data
        serialize = YearLevelSerializer(data=data)
        if serialize.is_valid():
            serialize.save()
            return Response(
                {"message": "Data Saved Successfully"}, status=status.HTTP_201_CREATED
            )
        return Response(
            {"message": "Insert Valid Data"}, status=status.HTTP_400_BAD_REQUEST
        )

    elif request.method == "PUT":
        if id is None:
            return Response(
                {"message": "Id is Required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = YearLevel.objects.get(pk=id)
            serialize = YearLevelSerializer(
                instance=data, data=request.data, partial=True
            )
            if serialize.is_valid():
                serialize.save()
                return Response(
                    {"message": "Data Updated Successfully"},
                    status=status.HTTP_202_ACCEPTED,
                )
            return Response(
                {"message": "Insert Valid Data"}, status=status.HTTP_400_BAD_REQUEST
            )
        except YearLevel.DoesNotExist:
            return Response(
                {"message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": "something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    elif request.method == "DELETE":
        if id is None:
            return Response(
                {"message": "Id is Required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = YearLevel.objects.get(pk=id)
            data.delete()
            return Response(
                {"message": "Data Deleted Successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )
        except YearLevel.DoesNotExist:
            return Response(
                {"message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"message": "something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["GET", "POST", "PUT", "DELETE"])
def SchoolYearView(request, pk=None):

    if request.method == "GET":
        if pk is not None:
            try:
                store = SchoolYear.objects.get(id=pk)
                serialize_rData = SchoolYearSerializer(store, many=False)
                return Response(serialize_rData.data, status=status.HTTP_200_OK)

            except SchoolYear.DoesNotExist:
                return Response(
                    {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
                )

        else:
            store = SchoolYear.objects.all()
            print("\n\n", store, "\n\n")
            serializerData = SchoolYearSerializer(store, many=True)
            return Response(serializerData.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        json_data = request.data
        serializerData = SchoolYearSerializer(data=json_data)

        if serializerData.is_valid():
            serializerData.save()
            return Response(
                {"Message": "School Year Added Successfully"},
                status=status.HTTP_201_CREATED,
            )

        return Response({"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        try:
            Store = SchoolYear.objects.get(id=pk)
            Updated_SchoolYear = SchoolYearSerializer(instance=Store, data=request.data)

            if Updated_SchoolYear.is_valid():
                Updated_SchoolYear.save()
                return Response(
                    {"message": "Update School Year Successfully"},
                    status=status.HTTP_201_CREATED,
                )

            return Response(
                {"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST
            )

        except SchoolYear.DoesNotExist:
            return Response(
                {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )

    elif request.method == "DELETE":
        try:
            store = SchoolYear.objects.get(id=pk)
            store.delete()
            return Response(
                {"Message": "School year Delete Successfuly"},
                status=status.HTTP_204_NO_CONTENT,
            )

        except SchoolYear.DoesNotExist:
            return Response(
                {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )


@api_view(["GET", "POST", "PUT", "DELETE"])
def DepartmentView(request, pk=None):
    if request.method == "GET":
        if pk is not None:
            try:
                department = Department.objects.get(id=pk)
                serializer = DepartmentSerializer(department, many=False)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except Department.DoesNotExist:
                return Response(
                    {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
                )

            except Exception as e:
                return Response(
                    {"Message": "Something went wrong"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        else:
            departments = Department.objects.all()
            serializer = DepartmentSerializer(departments, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        json_data = request.data

        if json_data.get("department_name", None) is None:
            return Response(
                {"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST
            )

        json_data["department_name"] = json_data["department_name"].lower()

        serializer = DepartmentSerializer(data=json_data)

        if serializer.is_valid():

            if Department.objects.filter(
                department_name=json_data["department_name"]
            ).exists():
                return Response(
                    {"Message": "Department Already Exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(
                {"Message": "Department Added Successfully"},
                status=status.HTTP_201_CREATED,
            )

        return Response({"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":

        if request.data.get("department_name", None) is None:
            return Response(
                {"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST
            )

        request.data["department_name"] = request.data["department_name"].lower()

        try:
            department = Department.objects.get(id=pk)
            serializer = DepartmentSerializer(instance=department, data=request.data)

            if serializer.is_valid():
                if Department.objects.filter(
                    department_name=request.data["department_name"].lower()
                ).exists():
                    return Response(
                        {"Message": "Department Already Exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                serializer.save()

                return Response(
                    {"Message": "Department updated Successfully"},
                    status=status.HTTP_201_CREATED,
                )

        except Department.DoesNotExist:
            return Response(
                {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"Message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    elif request.method == "DELETE":

        try:
            store = Department.objects.get(id=pk)
            store.delete()
            return Response(
                {"Message": "Department Delete Successfuly"},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Department.DoesNotExist:
            return Response(
                {"Message": "Data Not Found"}, status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"Message": "Something went wrong"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["GET", "POST", "PUT", "DELETE"])
def ClassRoomView(request, pk=None):

    def is_room_exists(room_type_id, room_name, exclude_id=None):
      
        queryset = ClassRoom.objects.filter(
            room_type_id=room_type_id,
            room_name__iexact=room_name.strip()
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

  
    if request.method == "GET":
        if pk:
            try:
                classroom = ClassRoom.objects.get(id=pk)
                serialize = ClassRoomSerializer(classroom)
                return Response(serialize.data, status=status.HTTP_200_OK)
            except ClassRoom.DoesNotExist:
                return Response({"Message": "Data not found"}, status=status.HTTP_404_NOT_FOUND)
        classrooms = ClassRoom.objects.all()
        serialize = ClassRoomSerializer(classrooms, many=True)
        return Response(serialize.data, status=status.HTTP_200_OK)


    elif request.method == "POST":
        room_type_id = request.data.get("room_type")
        room_name = request.data.get("room_name", "").strip()

        if not room_type_id or not room_name:
            return Response({"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

        if is_room_exists(room_type_id, room_name):
            return Response(
                {"Message": "This room already exists for this type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serialize = ClassRoomSerializer(data=request.data)
        if serialize.is_valid():
            serialize.save()
            return Response({"Message": "Data Saved Successfully"}, status=status.HTTP_200_OK)
        return Response({"Message": "Insert Valid Data", "Errors": serialize.errors},
                        status=status.HTTP_400_BAD_REQUEST)


    elif request.method == "PUT":
        try:
            classroom = ClassRoom.objects.get(id=pk)
        except ClassRoom.DoesNotExist:
            return Response({"Message": "Data not found"}, status=status.HTTP_404_NOT_FOUND)

        room_type_id = request.data.get("room_type")
        room_name = request.data.get("room_name", "").strip()

        if not room_type_id or not room_name:
            return Response({"Message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

        if is_room_exists(room_type_id, room_name, exclude_id=pk):
            return Response(
                {"Message": "This room already exists for this type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serialize = ClassRoomSerializer(instance=classroom, data=request.data)
        if serialize.is_valid():
            serialize.save()
            return Response({"Message": "Data Updated Successfully"}, status=status.HTTP_200_OK)
        return Response({"Message": "Insert Valid Data", "Errors": serialize.errors},
                        status=status.HTTP_400_BAD_REQUEST)

 
    elif request.method == "DELETE":
        try:
            classroom = ClassRoom.objects.get(id=pk)
            classroom.delete()
            return Response({"Message": "Data Deleted"}, status=status.HTTP_204_NO_CONTENT)
        except ClassRoom.DoesNotExist:
            return Response({"Message": "Data not found"}, status=status.HTTP_404_NOT_FOUND)




@api_view(["GET", "POST", "PUT", "DELETE"])
def ClassRoomTypeView(request, pk=None):

    if request.method == "GET":
        if pk is not None:
            try:
                classroom_type = ClassRoomType.objects.get(id=pk)
                serialize = ClassRoomTypeSerializer(classroom_type, many=False)
                return Response(serialize.data, status.HTTP_200_OK)

            except ClassRoomType.DoesNotExist:
                return Response(
                    {"Message": "Data not found"}, status.HTTP_404_NOT_FOUND
                )
        else:
            classroom_types = ClassRoomType.objects.all()
            serialized = ClassRoomTypeSerializer(classroom_types, many=True)
            return Response(serialized.data, status.HTTP_200_OK)

    elif request.method == "POST":
        data = request.data
        data["name"] = data["name"].lower()
        serialize = ClassRoomTypeSerializer(data=data)
        if serialize.is_valid():

            if ClassRoomType.objects.filter(name=data["name"]).exists():

                return Response(
                    {"Message": "Classroom Type Already Exist"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serialize.save()
            return Response({"Message": "Data Saved Successfully"}, status.HTTP_200_OK)
        return Response({"Message": "Insert Valid Data"}, status.HTTP_201_CREATED)

    elif request.method == "PUT":
        try:
            data = ClassRoomType.objects.get(id=pk)

            if request.data.get("name", None) is None:
                return Response(
                    {"Message": "Invalid Data"}, status.HTTP_400_BAD_REQUEST
                )

            request.data["name"] = request.data["name"].lower()

            serialize = ClassRoomTypeSerializer(instance=data, data=request.data)
            if serialize.is_valid():

                if ClassRoomType.objects.filter(
                    name=request.data["name"].lower()
                ).exists():
                    return Response(
                        {"Message": "Classroom Type Already Exist"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                serialize.save()
                return Response(
                    {"Message": "Data Updated Successfully"}, status.HTTP_200_OK
                )
            return Response(
                {"Message": "Insert Valid Data"}, status.HTTP_400_BAD_REQUEST
            )

        except ClassRoomType.DoesNotExist:
            return Response({"Message": "Data not found"}, status.HTTP_404_NOT_FOUND)

 
    elif request.method == "DELETE":
        try:
            data = ClassRoomType.objects.get(id=pk)
            data.delete()
            return Response({"Message": "Data Deleted"}, status.HTTP_204_NO_CONTENT)

        except ClassRoomType.DoesNotExist:
            return Response({"Message": "Data not found"}, status.HTTP_404_NOT_FOUND)


#

### --- Added this as of 06June25 at 12:00 PM

def get_or_create_role(role_name: str):
    role_name = role_name.strip().lower()
    role, created = Role.objects.get_or_create(
        name__iexact=role_name,
        defaults={"name": role_name}
    )
    return role

@api_view(["GET", "POST", "PUT", "DELETE"])
def RoleView(request, pk=None):
    if request.method == "GET":
        if pk:
            try:
                role = Role.objects.get(pk=pk)
                serializer = RoleSerializer(role)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Role.DoesNotExist:
                return Response({"message": "Role not found"}, status=status.HTTP_404_NOT_FOUND)
        else:
            roles = Role.objects.all()
            serializer = RoleSerializer(roles, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == "POST":
        role_name = request.data.get("name", "").strip().lower()

        if not role_name:
            return Response({"message": "Role name is required"}, status=status.HTTP_400_BAD_REQUEST)

        existing_role = Role.objects.filter(name__iexact=role_name).first()
        if existing_role:
            return Response({"message": "Role already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RoleSerializer(data={"name": role_name})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "New Role added Successfully"}, status=status.HTTP_201_CREATED)

        return Response({"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "PUT":
        if not pk:
            return Response({"message": "Role ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role = Role.objects.get(pk=pk)
        except Role.DoesNotExist:
            return Response({"message": "Role ID not Found"}, status=status.HTTP_404_NOT_FOUND)

        new_name = request.data.get("name", "").strip().lower()

        if not new_name:
            return Response({"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

        if Role.objects.exclude(pk=pk).filter(name__iexact=new_name).exists():
            return Response({"message": "Role with this name already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RoleSerializer(instance=role, data={"name": new_name})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Role updated Successfully"}, status=status.HTTP_200_OK)

        return Response({"message": "Invalid Data"}, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        if not pk:
            return Response({"message": "Role ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            role = Role.objects.get(pk=pk)
            role.delete()
            return Response({"message": "Role deleted Successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Role.DoesNotExist:
            return Response({"message": "Role not Found"}, status=status.HTTP_404_NOT_FOUND)





# ==============Country================
class CountryView(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    
# ==============Subject================
class subjectView(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = subjectSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        year_id = self.request.query_params.get('year_level')
        if year_id:
            qs = qs.filter(year_levels__id=year_id)
        return qs


# ===============State===================
class StateView(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer


# ================City===============
class CityView(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


# ===========Address==========



# ===========Period============


class PeriodView(viewsets.ModelViewSet):
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer


class DirectorView(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorProfileSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_instance = instance.user
        if user_instance.role.exclude(name="director").exists():
            try:
                role = Role.objects.get(name="director")
                user_instance.role.remove(role)
            except Role.DoesNotExist:
                pass
            self.perform_destroy(instance)
        else:
            instance.delete()
            user_instance.delete()
        return Response(
            {"success": "Successfully deleted"}, status=status.HTTP_204_NO_CONTENT
        )


# ==============Country================
class CountryView(viewsets.ModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer


# ===============State===================
class StateView(viewsets.ModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer


# ================City===============
class CityView(viewsets.ModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer


# ===========Address==========


# Added as of 28April25

class AddressView(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ===========Period============


class PeriodView(viewsets.ModelViewSet):
    queryset = Period.objects.all()
    serializer_class = PeriodSerializer
    
    
# class ClassPeriodView(viewsets.ModelViewSet):
#     queryset = ClassPeriod.objects.all()
#     serializer_class = ClassPeriodSerializer    


class DirectorView(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorProfileSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_instance = instance.user
        if user_instance.role.exclude(name="director").exists():
            try:
                role = Role.objects.get(name="director")
                user_instance.role.remove(role)
            except Role.DoesNotExist:
                pass
            self.perform_destroy(instance)
        else:
            instance.delete()
            user_instance.delete()
        return Response(
            {"success": "Successfully deleted"}, status=status.HTTP_204_NO_CONTENT
        )


class BankingDetailView(viewsets.ModelViewSet):
    queryset = BankingDetail.objects.all()
    serializer_class = BankingDetailsSerializer

class BankNameView(viewsets.ModelViewSet):
    queryset = BankName.objects.all()
    serializer_class = BankNameSerializer


class DirectorView(viewsets.ModelViewSet):
    queryset = Director.objects.all()
    serializer_class = DirectorProfileSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve','update', 'partial_update']:
            return [AllowAny()]  # Public access
        return [IsAuthenticated()]  # JWT required for others


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user_instance = instance.user
        if user_instance.role.exclude(name="director").exists():
            try:
                role = Role.objects.get(name="director")
                user_instance.role.remove(role)
            except Role.DoesNotExist:
                pass
            self.perform_destroy(instance)
        else:
            instance.delete()
            user_instance.delete()
        return Response(
            {"success": "Successfully deleted"}, status=status.HTTP_204_NO_CONTENT
        )
        
        
    # ******************JWt********************
    @action(detail=False, methods=['get', 'put', 'patch'], url_path='director_my_profile', permission_classes=[IsAuthenticated])
    def director_my_profile(self, request):
        user = request.user

        try:
            director = Director.objects.get(user=user)
        except Director.DoesNotExist:
            return Response({"error": "No director profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(director, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": "Director profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(director)
        return Response(serializer.data, status=status.HTTP_200_OK)    


class BankingDetails(viewsets.ModelViewSet):
    queryset = BankingDetail.objects.all()
    serializer_class = BankingDetailsSerializer


class TermView(viewsets.ModelViewSet):
    queryset =Term.objects.all()
    serializer_class = TermSerializer


from django_filters.rest_framework import DjangoFilterBackend  
# from .filters import AdmissionFilter
class AdmissionView(viewsets.ModelViewSet):
    queryset = Admission.objects.all()
    serializer_class = AdmissionSerializer

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    # filterset_class = AdmissionFilter

    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__user__email",
        "guardian__user__first_name",
        "guardian__user__last_name",
        "tc_letter",
        "enrollment_no",
        "previous_school_name",
    ]

    ordering_fields = [
        "admission_date",
        "year_level__level_name",
        "student__user__first_name",
        "previous_percentage",
    ]
    # parser_classes=[MultiPartParser,FormParser]
    

    # rte
    @action(detail=False, methods=["get"], url_path="rte-students")
    def rte_students(self, request):
        queryset = self.queryset.filter(is_rte=True)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
  
    
    
    
    # ***************OfficeStaffView**************
    
class OfficeStaffView(viewsets.ModelViewSet):
    queryset=OfficeStaff.objects.all()
    serializer_class = OfficeStaffSerializer  
    
    
    def get_permissions(self):
        # Public access to list and retrieve
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [AllowAny()]
        return [
            # IsAuthenticated()
                ]


    @action(detail=False, methods=['get','put', 'patch'], url_path='OfficeStaff_my_profile', permission_classes=[IsAuthenticated])
    def OfficeStaff_my_profile(self, request):
        user = request.user

        try:
            staff = OfficeStaff.objects.get(user=user)
        except OfficeStaff.DoesNotExist:
            return Response({"error": "No office staff profile found for this user."}, status=status.HTTP_404_NOT_FOUND)

        if request.method in ['PUT', 'PATCH']:
            partial = request.method == 'PATCH'
            serializer = self.get_serializer(staff, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response({"success": "Office staff profile updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

        serializer = self.get_serializer(staff)
        return Response(serializer.data, status=status.HTTP_200_OK)  
    
#  ***************************   
class DocumentTypeView(viewsets.ModelViewSet):
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer 
    
class FileView(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer 



# from rest_framework import viewsets, status
# from rest_framework.response import Response
# from django.db import transaction
# from .models import Document, File
# from .serializers import DocumentSerializer

# class DocumentView(viewsets.ModelViewSet):
#     queryset = Document.objects.prefetch_related('files', 'document_types')
#     serializer_class = DocumentSerializer

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         # Validate files
#         files = request.FILES.getlist('files')
#         if not files:
#             return Response({"error": "Files required"}, status=status.HTTP_400_BAD_REQUEST)

#         # Get and validate document types
#         doc_types = request.data.getlist('document_types', []) or [request.data.get('document_types')]
#         doc_types = [dt for dt in doc_types if dt and str(dt).isdigit()]  # Filter valid numeric types
#         if not doc_types:
#             return Response({"error": "Valid document types required"}, status=status.HTTP_400_BAD_REQUEST)

#         # Prepare data with null handling for empty strings
#         data = {
#             'document_types': doc_types,
#             'identities': request.data.get('identities'),
#             **{f: int(request.data[f]) if request.data.get(f) and str(request.data[f]).isdigit() else None 
#                for f in ['student', 'teacher', 'guardian', 'office_staff']}
#         }

#         # Find existing document
#         existing = self._find_existing_document(data)
        
#         # Create or update document
#         if existing:
#             serializer = self.get_serializer(existing, data=data, partial=True)
#             existing.files.all().delete()
#             action = 'replaced'
#         else:
#             serializer = self.get_serializer(data=data)
#             action = 'created'

#         serializer.is_valid(raise_exception=True)
#         doc = serializer.save()

#         # Save all uploaded files
#         for file in files:
#             File.objects.create(document=doc, file=file)

#         return Response({
#             'status': action,
#             'document': self.get_serializer(doc, context={'request': request}).data
#         }, status=status.HTTP_201_CREATED)

#     def _find_existing_document(self, data):
#         """Helper method to find existing document matching criteria"""
#         filter_params = {
#             'identities': data.get('identities'),
#             **{f: data.get(f) for f in ['student', 'teacher', 'guardian', 'office_staff'] 
#                if data.get(f) is not None}
#         }
        
#         for doc in Document.objects.filter(**filter_params).prefetch_related('document_types'):
#             if set(doc.document_types.values_list('id', flat=True)) == set(map(int, data['document_types'])):
#                 return doc
#         return None



from django.db import transaction


# class DocumentView(viewsets.ModelViewSet):
#     queryset = Document.objects.prefetch_related('files', 'document_types')
#     serializer_class = DocumentSerializer

#     @transaction.atomic
#     def create(self, request, *args, **kwargs):
#         # Validate files
#         files = request.FILES.getlist('files')
#         if not files:
#             return Response({"error": "Files required"}, status=status.HTTP_400_BAD_REQUEST)

#         # Get and validate document types
#         doc_types = request.data.getlist('document_types', []) or [request.data.get('document_types')]
#         doc_types = [dt for dt in doc_types if dt and str(dt).isdigit()]
#         if not doc_types:
#             return Response({"error": "Valid document types required"}, status=status.HTTP_400_BAD_REQUEST)

#         # Handle identities - accept both single value and array
#         identities = request.data.getlist('identities', []) or [request.data.get('identities')]
#         identities = [i for i in identities if i]  # Remove empty values
#         identities_str = ", ".join(identities) if identities else None

#         # Prepare data with null handling
#         data = {
#             'document_types': doc_types,
#             'identities': identities_str,  # Store all identities as comma-separated string
#             **{f: int(request.data[f]) if request.data.get(f) and str(request.data[f]).isdigit() else None 
#                for f in ['student', 'teacher', 'guardian', 'office_staff']}
#         }

#         # Find existing document
#         existing = self._find_existing_document(data)
        
#         # Create or update document
#         if existing:
#             # Delete old files first, so new ones replace them
#             existing.files.all().delete()
#             serializer = self.get_serializer(existing, data=data, partial=True)
#             action = 'replaced'
#         else:
#             serializer = self.get_serializer(data=data)
#             action = 'created'

#         serializer.is_valid(raise_exception=True)
#         doc = serializer.save()

#         # Save all uploaded files
#         for file in files:
#             File.objects.create(document=doc, file=file)

#         return Response({
#             'status': action,
#             'document': self.get_serializer(doc, context={'request': request}).data
#         }, status=status.HTTP_201_CREATED)

#     def _find_existing_document(self, data):
#         """Helper method to find existing document matching criteria"""
#         filter_params = {
#             **{f: data.get(f) for f in ['student', 'teacher', 'guardian', 'office_staff'] 
#                if data.get(f) is not None}
#         }
        
#         # If identities exist in data, include them in filter
#         if data.get('identities'):
#             filter_params['identities'] = data['identities']
        
#         for doc in Document.objects.filter(**filter_params).prefetch_related('document_types'):
#             if set(doc.document_types.values_list('id', flat=True)) == set(map(int, data['document_types'])):
#                 return doc
#         return None

class DocumentView(viewsets.ModelViewSet):
    queryset = Document.objects.prefetch_related('files', 'document_types')
    serializer_class = DocumentSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Validate files
        files = request.FILES.getlist('files')
        has_files = bool(files)

        # Get and validate document types
        doc_types = request.data.getlist('document_types', []) or [request.data.get('document_types')]
        doc_types = [dt for dt in doc_types if dt and str(dt).isdigit()]
        if not doc_types:
            return Response({"error": "Valid document types required"}, status=status.HTTP_400_BAD_REQUEST)

        # Handle identities - accept both single value and array
        identities = request.data.getlist('identities', []) or [request.data.get('identities')]
        identities = [i for i in identities if i]  # Remove empty values
        identities_str = ", ".join(identities) if identities else None

        # Prepare data with null handling
        data = {
            'document_types': doc_types,
            'identities': identities_str,  # Store all identities as comma-separated string
            **{f: int(request.data[f]) if request.data.get(f) and str(request.data[f]).isdigit() else None 
               for f in ['student', 'teacher', 'guardian', 'office_staff']}
        }

        # Find existing document
        existing = self._find_existing_document(data)

        # Create or update document
         # --- CASE 1: Update existing document ---
        if existing:
            msg_parts = []

            # Update identity if changed
            if identities_str and identities_str != existing.identities:
                existing.identities = identities_str
                existing.save(update_fields=['identities'])
                msg_parts.append("Identity updated")

            # Replace files if provided
            if has_files:
                existing.files.all().delete()
                for file in files:
                    File.objects.create(document=existing, file=file)
                msg_parts.append("Files replaced")

            # If no files or identity changes → show message
            if not msg_parts:
                return Response({
                    "status": "no_change",
                    "message": "No updates were made — identity and files are same as before.",
                    "document": self.get_serializer(existing, context={'request': request}).data
                }, status=status.HTTP_200_OK)

            return Response({
                "status": "updated",
                "message": " and ".join(msg_parts) + " successfully.",
                "document": self.get_serializer(existing, context={'request': request}).data
            }, status=status.HTTP_200_OK)
        
        # --- CASE 2: No existing doc → create new one ---
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()

        for file in files:
            File.objects.create(document=doc, file=file)

        return Response({
            "status": "created",
            "document": self.get_serializer(doc, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    def _find_existing_document(self, data):
        """Find existing document for same user + document type"""
        filter_params = {
            f: data.get(f)
            for f in ['student', 'teacher', 'guardian', 'office_staff']
            if data.get(f) is not None
        }

        existing_docs = Document.objects.filter(**filter_params).prefetch_related('document_types')

        for doc in existing_docs:
            existing_types = set(doc.document_types.values_list('id', flat=True))
            incoming_types = set(map(int, data['document_types']))
            if existing_types & incoming_types:  # intersection found
                return doc

        return None



# **************Assignment ClassPeriod for Student behalf of YearLevel(standard)****************   
    
# As of 05May25 at 01:00 PM

class ClassPeriodView(viewsets.ModelViewSet):
    queryset = ClassPeriod.objects.all()
    serializer_class = ClassPeriodSerializer
    
    @action(detail=False, methods=["post"], url_path="assign-to-yearlevel")
    def assign_to_yearlevel(self, request):
        serializer = ClassPeriodSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                "message": "ClassPeriods assigned successfully.",
                "details": result
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)    
    

from twilio.rest import Client 
def send_whatsapp_message(message_text):
    account_sid = 'AC75f0880296f2c1377b2ca30442bbd3e1'
    auth_token = '01dfff8731923c8e91e47b469f533fd5'
    twilio_whatsapp_number = 'whatsapp:+14155238886'
    
    phone_numbers = [
       '+918109145639',
        '+918102637122',
        '+919981993064'
    ]

    client = Client(account_sid, auth_token)

    sent_messages = []
    print('\n\n\n',sent_messages)
    for number in phone_numbers:
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

    return sent_messages


### --------------------- Income Distribution Dashboard API (Guardian name and student name and id added) --------------------------- ###
### ------------------- As of 03 JUly at 12:35 --------------- ###   By daniyal

@api_view(["GET"])
def guardian_income_distribution_with_student(request):
    # Define updated income brackets
    brackets = {
        "Below 1 Lakh": (0, 100000),
        "1 - 3 Lakhs": (100001, 300000),
        "3 - 5 Lakhs": (300001, 500000),
        "5 - 8 Lakhs": (500001, 800000),
        "8 - 10 Lakhs": (800001, 1000000),
        "Above 10 Lakhs": (1000001, None),
    }

    total_guardians = Guardian.objects.exclude(annual_income__isnull=True).count()
    results = []
    #---------- Count and guardian filter as it is
    for label, (min_income, max_income) in brackets.items():
        if max_income is not None:
            qs = Guardian.objects.filter(
                annual_income__gte=min_income,
                annual_income__lte=max_income
            )
        else:
            qs = Guardian.objects.filter(
                annual_income__gte=min_income,
            )  
        count = qs.count() 
        guardian_names = [f"{g.user.first_name} {g.user.last_name}" for g in qs]  

        student_data = [f" id:{s.studentguardian.get().student.id} {s.studentguardian.get().student.user.first_name} {s.studentguardian.get().student.user.last_name}" for s in qs]

        percentage = round((count / total_guardians) * 100, 2) if total_guardians > 0 else 0.0

        results.append({
            "income_range": label,
            "guardians":guardian_names,
            "count": count,
            "percentage": percentage,
            "student info": student_data
        })
        
    return Response(results, status=status.HTTP_200_OK)
### -------------------------------------------------------------- ###    


### --------------------- Deactivation of the users [NO access to them and data still stored] --------------------------- ###
### ------------------- As of 24 JUly at 12:00 --------------- ###   By daniyal
from rest_framework.decorators import permission_classes
from django.db import transaction
from authentication.models import UserStatusLog
from authentication.serializers import UserSerializer

# @api_view(["POST"])
# @permission_classes([RoleBasedUserManagementPermission])
# def deactivate_user(request):
#     deactivate_user.api_section = "deactivate_user" 
#     try:
#         with transaction.atomic():
#             user_id = request.data.get("user_id")
#             user = User.objects.all_including_inactive().get(id=user_id)
#             if not user.is_active:
#                 return Response({"error": "User already deactivated"})
#             user.is_active = False
#             user.deactivation_reason = request.data.get('reason', '')
#             user.deactivation_date = timezone.now()
#             user.reactivation_date = None
#             user.save()
            
#             # Handle Student    (classes [clear], admission, feeRecord, document, )
#             student = getattr(user, 'student', None)
#             if student is not None:
#                 student = user.student
#                 student.is_active = False
#                 student.save()
#                 # Clear Student.classes and StudentYearLevel 
#                 student.classes.clear()
#                 # Clear StudentYearLevel (handle missing studenyearlevel_set)
#                 try:
#                     StudentYearLevel.objects.filter(student=student).delete()
#                 except AttributeError:
#                     pass  # No StudentYearLevel relationship

#                 # Clear related Admissions
#                 admissions = Admission.objects.filter(student=student)
#                 for admission in admissions:
#                     admission.is_active = False
#                     admission.save()
#                 # Clear related FeeRecords
#                 fee_records = FeeRecord.objects.filter(student=student)
#                 for fee_record in fee_records:
#                     fee_record.is_active = False
#                     fee_record.save()
#                 # Clear related Documents
#                 documents = Document.objects.filter(student=student)
#                 for document in documents:
#                     document.is_active = False
#                     document.save()
#                 # Deactivate related Addresses
#                 addresses = Address.objects.filter(user=user)
#                 for address in addresses:
#                     address.is_active = False
#                     address.save()
#                 # Deactivate Banking Details
#                 bank_details = BankingDetail.objects.filter(user=user)
#                 for bank_detail in bank_details:
#                     bank_detail.is_active = False
#                     bank_detail.save()    

#             # Handle Guardian   (Student guardian relation [clear], address, docs)
#             guardian = getattr(user, 'guardian_relation', None)
#             if guardian is not None:
#                 guardian = user.guardian_relation
#                 guardian.is_active = False
#                 guardian.save()
#                 # Clear StudentGuardian connections
#                 student_guardians = StudentGuardian.objects.filter(guardian=guardian)
#                 for sg in student_guardians:
#                     sg.delete()  # Clear the relationship
#                 # Deactivate related Addresses
#                 addresses = Address.objects.filter(user=user)
#                 for address in addresses:
#                     address.is_active = False
#                     address.save()
#                 # Clear related Documents
#                 documents = Document.objects.filter(guardian=guardian)
#                 for document in documents:
#                     document.is_active = False
#                     document.save() 
                
#             # Handle Teacher  (classPeriod [clear {M2M}], address, docs)
#             teacher = getattr(user, 'teacher', None)
#             if teacher is not None:
#                 teacher = user.teacher
#                 teacher.is_active = False
#                 teacher.save()

#                 # Clear TeacherYearLevel connections
#                 teacher.year_levels.clear()
#                 # Remove teacher from ClassPeriod assignments
#                 class_periods = ClassPeriod.objects.filter(teacher=teacher)
#                 for cp in class_periods:
#                     cp.teacher = None  # Set to None to remove assignment
#                     cp.save()
#                 ClassPeriod.objects.filter(teacher=teacher).delete()
#                 # Deactivate related Addresses
#                 addresses = Address.objects.filter(user=user)
#                 for address in addresses:
#                     address.is_active = False
#                     address.save()
#                 # Clear related Documents
#                 documents = Document.objects.filter(teacher=teacher)
#                 for document in documents:
#                     document.is_active = False
#                     document.save()    
                    

#             # Handle OfficeStaff  ([student,teacher,admission {clear M2M}, address, docs])
#             office_staff = getattr(user, 'office_staff', None)
#             if office_staff is None:
#                 # Attempt to fetch OfficeStaff directly to confirm relation
#                 try:
#                     office_staff = OfficeStaff.objects.get(user=user)
#                 except OfficeStaff.DoesNotExist:
#                     print(f"No OfficeStaff found for user {user.id} via query")
#             else:
#                 try:
#                     office_staff.is_active = False
#                     office_staff.save()
#                     # Clear ManyToMany relationships
#                     office_staff.student.clear()
#                     office_staff.teacher.clear()
#                     office_staff.admissions.clear()
#                     # Deactivate related Addresses
#                     addresses = Address.objects.filter(user=user)
#                     for address in addresses:
#                         address.is_active = False
#                         address.save()
#                     # Clear related Documents
#                     documents = Document.objects.filter(office_staff=office_staff)
#                     for document in documents:
#                         document.is_active = False
#                         document.save()
#                 except Exception as e:
#                     return Response({"error": f"Failed to deactivate OfficeStaff: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
#             # Handle Director (if needed)
#             director = getattr(user, 'director', None)
#             if director is not None:
#                 director = user.director
#                 director.is_active = False
#                 director.save()
#                 # Deactivate related Addresses
#                 addresses = Address.objects.filter(user=user)
#                 for address in addresses:
#                     address.is_active = False
#                     address.save()

#             # log termination
#             UserStatusLog.objects.create(user=user, status='TERMINATED', reason=user.deactivation_reason)
#             serializer = UserSerializer(user)
#             return Response({
#                 "message": f"User {user.id} has been successfully terminated.",
#                 "user_id": user.id,
#                 "data": serializer.data})
#     except User.DoesNotExist:
#         return Response({"error": "User not found"})
 
### -------------------------------------------------------------- ###

# *************** Reactivation of the User *******************************************************
# from django.core.exceptions import ObjectDoesNotExist

# @api_view(["POST"])
# @permission_classes([RoleBasedUserManagementPermission])
# def reactivate_user(request):
#     reactivate_user.api_section = "reactivate_user" 
#     try:
#         with transaction.atomic():
#             user_id = request.data.get("user_id")
#             user = User.objects.all_including_inactive().get(id=user_id)
#             if user.is_active:
#                 return Response({"error": "User already active"})
#             user.is_active = True
#             user.deactivation_reason = None
#             user.reactivation_date = timezone.now()
#             user.save()
            
#             # Handle Student    ([classes {make}, studentyearlevel, studentguardian] , admission, feeRecord, document, address,
#             # banking details )
#             student = getattr(user, 'student', None)
#             if student is not None:
#                 student = user.student
#                 student.is_active = True
#                 student.save()

#                 # retrieve related Admissions
#                 admissions = Admission.objects.all_including_inactive().filter(student=student)
#                 for admission in admissions:
#                     admission.is_active = True
#                     admission.save()
#                 # retrieve related FeeRecords
#                 fee_records = FeeRecord.objects.all_including_inactive().filter(student=student)
#                 for fee_record in fee_records:
#                     fee_record.is_active = True
#                     fee_record.save()
#                 # retrieve related Documents
#                 documents = Document.objects.all_including_inactive().filter(student=student)
#                 for document in documents:
#                     document.is_active = True
#                     document.save()
#                 # retrieve related Addresses
#                 addresses = Address.objects.all_including_inactive().filter(user=user)
#                 for address in addresses:
#                     address.is_active = True
#                     address.save()
#                 # retrieve Banking Details
#                 bank_details = BankingDetail.objects.all_including_inactive().filter(user=user)
#                 for bank_detail in bank_details:
#                     bank_detail.is_active = True
#                     bank_detail.save() 

                
#                 # Create Student.classes connection
#                 class_period_ids = request.data.get("class_period_ids", [])
#                 if class_period_ids:
#                     valid_class_period = ClassPeriod.objects.filter(id__in=class_period_ids)
#                     if valid_class_period:
#                         student.classes.set(valid_class_period)
#                     else:
#                         return Response({"erorr": "Invalid class period ids"})
                    
#                 # Create StudentYearLevel connection 
#                 year_id = request.data.get("year_id")
#                 level_id = request.data.get("level_id")
                
#                 if year_id and level_id:
#                     try:
#                         level = YearLevel.objects.get(id=level_id)
#                         year = SchoolYear.objects.get(id=year_id)
#                         StudentYearLevel.objects.update_or_create(
#                             student = student,
#                             defaults={"year": year, "level": level}
#                         )
#                     except ObjectDoesNotExist:
#                         return Response({"error":"Invalid year level id"})
                    
#                 # Create StudentGuardian connections
#                 guardian_ids = request.data.get("guardian_ids", [])
#                 if guardian_ids:
#                     valid_guardians = Guardian.objects.filter(id__in=guardian_ids, is_active=True)
#                     if valid_guardians.exists():
#                         guardian_type_id = request.data.get("guardian_type_id")
#                         try:
#                             guardian_type = GuardianType.objects.get(id=guardian_type_id) if guardian_type_id else GuardianType.objects.get(name="Parent")
#                             for guardian in valid_guardians:
#                                 StudentGuardian.objects.update_or_create(
#                                     student=student,
#                                     guardian=guardian,
#                                     defaults={'guardian_type': guardian_type}
#                                 )
#                         except ObjectDoesNotExist:
#                             return Response({"error": "Invalid or inactive GuardianType ID provided"}, status=status.HTTP_400_BAD_REQUEST)
#                     else:
#                         return Response({"error": "No valid or active Guardian IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
                    

#             # Handle Guardian   (Student guardian relation [make], address, docs)
#             guardian = getattr(user, 'guardian_relation', None)
#             if guardian is not None:
#                 guardian = user.guardian_relation
#                 guardian.is_active = True
#                 guardian.save()

#                 # update StudentGuardian connections
#                 student_ids = request.data.get("student_ids", [])
#                 if student_ids:
#                     valid_students = Student.objects.filter(id__in=student_ids, is_active=True)
#                     if valid_students.exists():
#                         guardian_type_id = request.data.get("guardian_type_id")
#                         try:
#                             guardian_type = GuardianType.objects.get(id=guardian_type_id) if guardian_type_id else GuardianType.objects.get(name="Parent")  
#                             for student in valid_students:
#                                 StudentGuardian.objects.update_or_create(
#                                     student=student,
#                                     guardian=guardian,
#                                     defaults={'guardian_type': guardian_type}
#                                 )
#                         except ObjectDoesNotExist:
#                             return Response({"error": "Invalid or inactive GuardianType ID provided"})
#                     else:
#                         return Response({"error": "No valid or active Student IDs provided"})
                
#                 # retrieve related Addresses
#                 addresses = Address.objects.all_including_inactive().filter(user=user)
#                 for address in addresses:
#                     address.is_active = True
#                     address.save()
#                 # retrieve related Documents
#                 documents = Document.objects.all_including_inactive().filter(guardian=guardian)
#                 for document in documents:
#                     document.is_active = True
#                     document.save() 
                
#             # Handle Teacher  (classPeriod [create {M2M}], teacheryearlevel, address, docs)
#             teacher = getattr(user, 'teacher', None)
#             if teacher is not None:
#                 teacher = user.teacher
#                 teacher.is_active = True
#                 teacher.save()

#                 # Assign teacher from ClassPeriod assignments
#                 class_period_ids = request.data.get("class_period_ids", [])
#                 if class_period_ids:
#                     valid_class_periods = ClassPeriod.objects.filter(id__in=class_period_ids)
#                     if valid_class_periods.exists():
#                         for class_period in valid_class_periods:
#                             class_period.teacher = teacher
#                             class_period.save()
#                     else:
#                         return Response({"error": "No valid or active ClassPeriod IDs provided"})

#                 # Teacher year level reassigning
#                 year_level_id = request.data.get("year_level_id", [])
#                 if year_level_id:
#                     valid_year_levels = YearLevel.objects.filter(id=year_level_id)
#                     if valid_year_levels.exists():
#                         teacher.year_levels.set(valid_year_levels)
#                     else:
#                         return Response({"error": "No valid or active YearLevel IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

#                 # retrieve related Addresses
#                 addresses = Address.objects.all_including_inactive().filter(user=user)
#                 for address in addresses:
#                     address.is_active = True
#                     address.save()
#                 # retrieve related Documents
#                 documents = Document.objects.all_including_inactive().filter(teacher=teacher)
#                 for document in documents:
#                     document.is_active = True
#                     document.save()    
                    

#             # Handle OfficeStaff  ([student,teacher,admisson {clear M2M}, address, docs])
#             office_staff = getattr(user, 'office_staff', None)
#             if office_staff is not None:
#                 office_staff = user.office_staff
#                 office_staff.is_active = True
#                 office_staff.save()

#                 # # Create ManyToMany relationships
#                 #  Student connection
#                 student_ids = request.data.get("student_ids", [])
#                 if student_ids:
#                     valid_students = Student.objects.filter(id__in=student_ids, is_active=True)
#                     if valid_students.exists():
#                         office_staff.student.set(valid_students)
#                     else:
#                         return Response({"error": "No valid or active Student IDs provided"})

#                 # Teacher connection
#                 teacher_ids  = request.data.get("teacher_ids", [])
#                 if teacher_ids:
#                     valid_teachers = Teacher.objects.filter(id__in=teacher_ids, is_active=True)
#                     if valid_teachers.exists():
#                         office_staff.teacher.set(valid_teachers)
#                     else:
#                         return Response({"error": "No valid or active Teacher IDs provided"})

#                 # Admission connection
#                 admission_ids = request.data.get("admission_ids", [])
#                 if admission_ids:
#                     valid_admissions = Admission.objects.filter(id__in=admission_ids, is_active=True)
#                     if valid_admissions.exists():
#                         office_staff.admissions.set(valid_admissions)
#                     else:
#                         return Response({"error":"No valid or active Admission IDs provided"})
                    

#                 # retrieve related Addresses
#                 addresses = Address.objects.all_including_inactive().filter(user=user)
#                 for address in addresses:
#                     address.is_active = True
#                     address.save()
#                 # retrieve related Documents
#                 documents = Document.objects.all_including_inactive().filter(office_staff=office_staff)
#                 for document in documents:
#                     document.is_active = True
#                     document.save() 

            
#             # Handle Director (if needed)
#             director = getattr(user, 'director', None)
#             if director is not None:
#                 director = user.director
#                 director.is_active = True
#                 director.save()
#                 # Deactivate related Addresses
#                 addresses = Address.objects.all_including_inactive().filter(user=user)
#                 for address in addresses:
#                     address.is_active = True
#                     address.save()

#             # log termination
#             UserStatusLog.objects.create(user=user, status='ACTIVATED', reason=user.deactivation_reason)
#             serializer = UserSerializer(user)
#             return Response({
#                 "message": f"User {user.id} has been successfully reactivated.",
#                 "user_id": user.id,
#                 "data": serializer.data})
#     except User.DoesNotExist:
#         return Response({"error": "User not found"})
    
### -------------------------------------------------------------- ###
# *************** List of the Deactivated *******************************************************

@api_view(["GET"])
def list_inactive_users(request):
    users = User.objects.all_including_inactive().filter(is_active=False)
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


#--------------------- Exam Module 

from django.apps import apps
from .utils import * 

class DownloadFileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        model_name = request.query_params.get("model")
        object_id = request.query_params.get("id")
        file_field_name = request.query_params.get("field", "uploaded_file")
        print(user,model_name,object_id,file_field_name)
        if not model_name or not object_id:
            return Response({"error": "model and id are required."}, status=400)

        try:
            model = apps.get_model(app_label="director", model_name=model_name)
        except LookupError:
            return Response({"error": f"Model '{model_name}' not found."}, status=404)

        instance = get_object_or_404(model, pk=object_id)

        user_roles = [role.name.lower() for role in user.role.all()]

        is_director = "director" in user_roles
        is_office = "office_staff" in user_roles
        is_teacher = "teacher" in user_roles
        is_student = "student" in user_roles
        is_guardian = "guardian" in user_roles

        student_related_id = getattr(instance, "student_id", None) or getattr(instance, "student", None)

        if is_student:
            if not StudentYearLevel.objects.filter(user=user, id=student_related_id).exists():
                return Response({"error": "Access denied: not your file."}, status=403)

        elif is_guardian:
            if not StudentGuardian.objects.filter(guardian=user, student_id=student_related_id).exists():
                return Response({"error": "Access denied: not your ward's file."}, status=403)

        elif is_teacher:
            assigned_classes = TeacherYearLevel.objects.filter(teacher=user).values_list("year_level_id", flat=True)
            student_obj = StudentYearLevel.objects.filter(id=student_related_id).first()
            if not student_obj or student_obj.year_level_id not in assigned_classes:
                return Response({"error": "Access denied: not your class student."}, status=403)

        elif not (is_director or is_office):
            return Response({"error": "Access denied: unauthorized role."}, status=403)

        file_field = getattr(instance, file_field_name, None)
        if not file_field:
            return Response({"error": f"Field '{file_field_name}' not found on model '{model_name}'."}, status=404)

        if not file_field.name:
            return Response({"error": f"{model_name} file not found."}, status=404)

        file_path = file_field.path
        print("File name:", file_field.name)
        print("File path:", file_field.path)
        print("File exists:", os.path.exists(file_field.path))


        if not os.path.exists(file_path):
            return Response({"error": f"{model_name} file not found."}, status=404)
        

        return get_file_response(file_field, file_label=f"{model_name} file")



class ExamTypeView(viewsets.ModelViewSet):
    queryset = ExamType.objects.all()
    serializer_class = ExamTypeSerializer
    permission_classes = [IsAuthenticated, RoleBasedExamPermission]
    api_section = 'exam_type'

    # @action(detail=False, methods=["get"], url_path="get_examtype")
    # def get_examtypes(self, request):
    #     exam_types = self.get_queryset()
    #     serializer = self.get_serializer(exam_types, many=True)
    #     return Response(serializer.data)

    # @action(detail=False, methods=["post"], url_path="create_examtype")
    # def create_examtype(self, request):
    #     name = request.data.get("name")
    #     if not name:
    #         return Response({"error": "Name is required."}, status=400)

    #     exam_type, created = ExamType.objects.get_or_create(name=name)
    #     serializer = self.get_serializer(exam_type)
    #     message = "Exam type created successfully." if created else "Exam type already exists."
    #     return Response({"message": message, "data": serializer.data}, status=201 if created else 200)

    # @action(detail=False, methods=["put"], url_path="update_examtype")
    # def update_examtype(self, request):
    #     try:
    #         exam_type = ExamType.objects.get(id=request.data.get("id"))
    #     except ExamType.DoesNotExist:
    #         return Response({"error": "ExamType not found"}, status=404)

    #     serializer = self.get_serializer(exam_type, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         serializer.save()
    #         return Response({"message": "Exam type updated successfully", "data": serializer.data})
    #     return Response(serializer.errors, status=400)

    # @action(detail=False, methods=["delete"], url_path="delete_examtype")
    # def delete_examtype(self, request):
    #     try:
    #         exam_type = ExamType.objects.get(id=request.data.get("id"))
    #         exam_type.delete()
    #         return Response({"message": "ExamType deleted successfully."})
    #     except ExamType.DoesNotExist:
    #         return Response({"error": "ExamType not found"}, status=404)



class ExamPaperView(viewsets.ModelViewSet):
    queryset = ExamPaper.objects.all()
    serializer_class = ExamPaperSerializer
    permission_classes = [IsAuthenticated, RoleBasedExamPermission]
    api_section = 'exam_paper'

    @action(detail=False, methods=["get"], url_path="get_exampaper")
    def get_exampapers(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if "director" in role_names or "office staff" in role_names:
            queryset = ExamPaper.objects.select_related('exam_type', 'term', 'subject', 'year_level', 'teacher')
        
        elif "teacher" in role_names:
            teacher = Teacher.objects.filter(user=user).first()
            queryset = ExamPaper.objects.filter(teacher=teacher).select_related('exam_type', 'term', 'subject', 'year_level', 'teacher')
        
        else:
            return Response({"error": "You do not have permission to view exam papers."}, status=403)
        # Filters from query params
        subject_id = request.query_params.get("subject")
        teacher_id = request.query_params.get("teacher")
        school_year = request.query_params.get("school_year")
        paper_code = request.query_params.get("paper_code")
        exam_type_id = request.query_params.get("exam_type")
        class_id = request.query_params.get("class")

        if subject_id:
            queryset = queryset.filter(subject__subject_name=subject_id)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if school_year:
            queryset = queryset.filter(term__year__year_name=school_year)
        if paper_code:
            queryset = queryset.filter(paper_code__icontains=paper_code)
        if exam_type_id:
            queryset = queryset.filter(exam_type__name=exam_type_id)
        if class_id:
            queryset = queryset.filter(year_level__level_name=class_id)
        if not queryset.exists():
            return Response([])

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=["post"], url_path="create_exampaper")
    def create_paper(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if "director" in role_names:
            pass  
        
        elif "teacher" in role_names:
            teacher = Teacher.objects.filter(user=user).first()
            if not teacher:
                return Response({"error": "Teacher not found."}, status=400)

            assigned_class_ids = TeacherYearLevel.objects.filter(
                teacher=teacher
            ).values_list('year_level_id', flat=True)

            class_name = request.data.get("year_level")  

            if class_name is None:
                return Response({"error": "year_level is required."}, status=400)

            try:
                class_name = int(class_name)
            except ValueError:
                return Response({"error": "Invalid year_level value."}, status=400)

            if class_name not in assigned_class_ids:
                return Response("You can only create papers for your assigned classes.", status=403)
        
        else:
            return Response("You do not have permission to create exam papers.", status=403)

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Exam paper created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["put"], url_path="update_exampaper")
    def update_paper(self, request):
        # Prefer updating by `id` (primary key). If not provided, fall back to `paper_code`.
        paper_id = request.data.get("id")
        paper_code = request.data.get("paper_code")

        paper = None
        if paper_id is not None:
            try:
                paper = ExamPaper.objects.get(id=paper_id)
            except (ValueError, TypeError):
                return Response({"error": "Invalid id provided."}, status=400)
            except ExamPaper.DoesNotExist:
                return Response({"error": "ExamPaper not found for given id."}, status=404)
        elif paper_code:
            try:
                paper = ExamPaper.objects.get(paper_code=paper_code)
            except ExamPaper.DoesNotExist:
                return Response({"error": "ExamPaper not found for given paper_code."}, status=404)
        else:
            return Response({"error": "Either 'id' or 'paper_code' is required for update."}, status=400)
        
        serializer = self.get_serializer(paper, data=request.data, partial=True)
        if serializer.is_valid():
            print(serializer.validated_data)
            serializer.save()
            return Response({
                "message": "Exam paper updated successfully", 
                "data": serializer.data
            })
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=["delete"], url_path="delete_exampaper")
    def delete_paper(self, request):
        paper_ids = request.data.get("paper_ids")
        if not paper_ids:
            return Response({"error": "paper_ids list is required."}, status=400)

        deleted = 0
        for pid in paper_ids:
            try:
                paper = ExamPaper.objects.get(id=pid)
                paper.delete()
            except ExamPaper.DoesNotExist:
                continue

        return Response({"message": "Successfully deleted paper(s)."})

from teacher.models import *
from django.db.models import Q
class ExamScheduleView(viewsets.ModelViewSet):
    queryset = ExamSchedule.objects.all()
    serializer_class = ExamScheduleSerializer
    permission_classes = [IsAuthenticated, RoleBasedExamPermission]
    api_section = 'exam_schedule'


    @staticmethod
    def format_exam_schedule(queryset):
        grouped_data = {}
        group_id_counter = 1

        for obj in queryset:
            key = f"{obj.class_name.id}_{obj.term.year.id}_{obj.exam_type.id}"

            if key not in grouped_data:
                grouped_data[key] = {
                    "id": group_id_counter,
                    "class": obj.class_name.level_name,
                    "school_year": f"{obj.term.year.year_name}- Term {obj.term.term_number}",
                    "exam_type": obj.exam_type.name,
                    "papers": []
                }
                group_id_counter += 1

            grouped_data[key]["papers"].append({
                "subject_name": obj.subject.subject_name.lower(),
                "exam_date": obj.exam_date,
                "start_time": obj.start_time,
                "end_time": obj.end_time,
                "day": obj.exam_date.strftime('%A')
            })

        return list(grouped_data.values())
    
    


    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="get_timetable")
    def get_timetable(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if "director" in role_names or "office staff" in role_names:
            queryset = ExamSchedule.objects.select_related("class_name", "term__year", "exam_type", "subject").all()

        elif "teacher" in role_names:
            teacher = Teacher.objects.filter(user=user).first()
            if not teacher:
                return Response({"error": "Teacher not found"}, status=400)
            assigned_class_ids = TeacherYearLevel.objects.filter(
                teacher=teacher
            ).values_list("year_level_id", flat=True)
            queryset = ExamSchedule.objects.select_related(
                "class_name", "term__year", "exam_type", "subject"
            ).filter(class_name_id__in=assigned_class_ids)

        elif "student" in role_names:
            student = Student.objects.filter(user=user).first()
            student_class = StudentYearLevel.objects.filter(student=student).last()
            if not student_class:
                return Response({"error": "Student class not found"}, status=400)
            queryset = ExamSchedule.objects.select_related(
                "class_name", "term__year", "exam_type", "subject"
            ).filter(class_name=student_class.level)

        else:
            return Response({"error": "Access Denied"}, status=403)

        # Apply filters from query params
        class_name = request.query_params.get("class_name")
        school_year = request.query_params.get("school_year")
        subject = request.query_params.get("subject")
        exam_type = request.query_params.get("exam_type")
        schedule_id = request.query_params.get("id")
        exam_date = request.query_params.get("exam_date")  

        if schedule_id:
            try:
                record = ExamSchedule.objects.get(id=schedule_id)
            except ExamSchedule.DoesNotExist:
                return Response({"error": "Schedule not found"}, status=404)

            queryset = ExamSchedule.objects.filter(
                class_name=record.class_name,
                term=record.term,
                exam_type=record.exam_type
            )

        if exam_date:
            queryset = queryset.filter(exam_date=exam_date)  


        if class_name:
            queryset = queryset.filter(class_name__level_name__iexact=class_name)
        if school_year:
            queryset = queryset.filter(term__year__year_name__iexact=school_year)
        # if subject:
        #     queryset = queryset.filter(subject__name__iexact=subject)
        if subject:
            queryset = queryset.filter(subject__subject_name__iexact=subject)

        if exam_type:
            queryset = queryset.filter(exam_type__name__iexact=exam_type)

        if not queryset.exists():
            return Response([])

        return Response(self.format_exam_schedule(queryset))








    
    # @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="get_timetable")
    # def get_timetable(self, request):
    #     user = request.user
    #     role_names = [role.name.lower() for role in user.role.all()]

    #     if "director" in role_names:
    #         queryset = ExamSchedule.objects.select_related("class_name", "term__year", "exam_type", "subject").all()

    #     elif "teacher" in role_names or "office staff" in role_names:
    #         teacher = Teacher.objects.filter(user=user).first()
    #         if not teacher:
    #             return Response({"error": "Teacher not found"}, status=400)
    #         assigned_class_ids = TeacherYearLevel.objects.filter(teacher=teacher).values_list('year_level_id', flat=True)
    #         queryset = ExamSchedule.objects.select_related("class_name", "term__year", "exam_type", "subject").filter(class_name_id__in=assigned_class_ids)

    #     elif "student" in role_names:
    #         student = Student.objects.filter(user=user).first()
    #         student_class = StudentYearLevel.objects.filter(student=student).last()
    #         if not student_class:
    #             return Response({"error": "Student class not found"}, status=400)
    #         queryset = ExamSchedule.objects.select_related("class_name", "term__year", "exam_type", "subject").filter(class_name=student_class.level)

    #     else:
    #         return Response({"error": "Access Denied"}, status=403)

    #     if not queryset.exists():
    #         return Response([])

    #     return Response(self.format_exam_schedule(queryset))




    
    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated], url_path="create_timetable")
    def create_timetable(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if any(role in role_names for role in ["director", "teacher", "office staff"]):
            serializer = ExamScheduleSerializer(data=request.data)
            if serializer.is_valid():
                schedules = serializer.save()
                return Response({"message": f"exam schedule created successfully."}, status=201)
            return Response(serializer.errors, status=400)

        return Response({"error": "You do not have permission to create timetable."}, status=403)



    @action(detail=False, methods=["put"], permission_classes=[IsAuthenticated], url_path="update_timetable")
    def update_timetable(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if not any(role in role_names for role in ["director", "teacher"]):
            return Response({"error": "Permission denied"})

        class_id = request.data.get("class_name")
        year_id = request.data.get("school_year")
        exam_type_id = request.data.get("exam_type")
        print(class_id,year_id,exam_type_id)
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            result = serializer.update(None, serializer.validated_data)  
            return Response({
                "message": "Exam timetable updated successfully.",
                "data": result
            }, status=200)

        return Response(serializer.errors, status=400)



# class StudentMarksView(viewsets.ModelViewSet):
#     queryset = StudentMarks.objects.all()
#     serializer_class = StudentMarksSerializer
#     permission_classes = [IsAuthenticated,RoleBasedExamPermission] 
#     api_section = "student_marks"  

#     @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="get_marks")
#     def get_marks(self, request):
#         user = request.user
#         role_names = [role.name.lower() for role in user.role.all()]

#         if "director" in role_names:
#             marks_qs = StudentMarks.objects.select_related(
#                 "student__student__user",
#                 "subject",
#                 "teacher__user",
#                 "exam_type",
#                 "term__year",
#                 "student__level"
#             )
#         elif "teacher" in role_names:
#             try:
#                 teacher = Teacher.objects.get(user=user)
#             except Teacher.DoesNotExist:
#                 return Response({"error": "Teacher not found."})

#             assigned_class_ids = TeacherYearLevel.objects.filter(
#                 teacher=teacher
#             ).values_list("year_level_id", flat=True)

#             student_ids = StudentYearLevel.objects.filter(
#                 level_id__in=assigned_class_ids
#             ).values_list("id", flat=True)

#             marks_qs = StudentMarks.objects.select_related(
#                 "student__student__user",
#                 "subject",
#                 "teacher__user",
#                 "exam_type",
#                 "term__year",
#                 "student__level"
#             ).filter(
#                 student_id__in=student_ids,
#                 teacher=teacher
#             )
#         else:
#             return Response({"error": "You do not have permission to view marks."})

#         # ----------- Filter
#         school_year_filter = request.query_params.get("school_year")
#         year_level_filter = request.query_params.get("year_level")
#         exam_type_filter = request.query_params.get("exam_type")
#         student_id = request.query_params.get("student_id")  
#         if student_id:
#             marks_qs = marks_qs.filter(student_id=student_id)

#         if school_year_filter:
#             marks_qs = marks_qs.filter(term__year__year_name=school_year_filter)
#         if year_level_filter:
#             marks_qs = marks_qs.filter(student__level__level_name=year_level_filter)
#         if exam_type_filter:
#             marks_qs = marks_qs.filter(exam_type__name=exam_type_filter)

#         if not marks_qs.exists():
#             return Response({"message": "No data found."})

#         grouped_data = {}
#         for mark in marks_qs:
#             teacher_name = mark.teacher.user.get_full_name().lower()
#             subject_name = mark.subject.subject_name.lower()
#             exam_type = mark.exam_type.name
#             school_year = mark.term.year.year_name
#             year_level = mark.student.level.level_name
#             key = (teacher_name, subject_name, exam_type, school_year, year_level)

#             grouped_data.setdefault(key, []).append({
#                 "name": mark.student.student.user.get_full_name().lower(),
#                 "marks": mark.marks_obtained
#             })

#         final_response = {}
#         for (teacher_name, subject_name, exam_type, school_year, year_level), student_marks in grouped_data.items():
#             group_key = (school_year, exam_type, year_level)
#             final_response.setdefault(group_key, []).append({
#                 "teacher_name": teacher_name,
#                 "subject": subject_name,
#                 "student_marks": student_marks
#             })

#         formatted_output = {}
#         for (school_year, exam_type, year_level), data in final_response.items():
#             marks_filtered = marks_qs.filter(
#                 term__year__year_name=school_year,
#                 exam_type__name=exam_type,
#                 student__level__level_name=year_level
#             )
#             first_mark = marks_filtered.first()
#             report_id = first_mark.id if first_mark else None
#             report_key = f"id : {report_id}" if report_id else f"{school_year}_{exam_type}_{year_level}".replace(" ", "_").lower()

#             formatted_output[report_key] = {
#                 "school_year": school_year,
#                 "exam_type": exam_type,
#                 "year_level": year_level,
#                 "data": data
#             }

#         return Response(formatted_output)



#     @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='create_marks')
#     def create_marks(self, request):
#         user = request.user
#         role_names = [role.name.lower() for role in user.role.all()]

#         is_director = "director" in role_names
#         is_teacher = "teacher" in role_names

#         if not (is_director or is_teacher):
#             return Response({"error": "You do not have permission to perform this action."})

#         if is_teacher:
#             try:
#                 teacher = Teacher.objects.get(user=user)
#             except Teacher.DoesNotExist:
#                 return Response({"error": "Teacher not found."})
#             assigned_class_ids = TeacherYearLevel.objects.filter(
#                 teacher=teacher
#             ).values_list("year_level_id", flat=True)
#         else:
#             teacher = None
#             assigned_class_ids = []

#         data = request.data
#         school_year_id = data.get("school_year_id")
#         exam_type_id = data.get("exam_type_id")
#         year_level_id = data.get("year_level_id")

#         # print("school_year_id:", school_year_id)
#         # print("exam_type_id:", exam_type_id)
#         # print("year_level_id:", year_level_id)

#         if not school_year_id or not exam_type_id or not year_level_id:
#             return Response({
#                 "error": "Missing required fields: school_year_id, exam_type_id, or year_level_id"
#             }, status=400)

#         try:
#             school_year_obj = SchoolYear.objects.get(id=school_year_id)
#             exam_type_obj = ExamType.objects.get(id=exam_type_id)
#             year_level_obj = YearLevel.objects.get(id=year_level_id)
#         except SchoolYear.DoesNotExist:
#             return Response({"error": "Invalid school_year"})
#         except ExamType.DoesNotExist:
#             return Response({"error": "Invalid exam_type"})
#         except YearLevel.DoesNotExist:
#             return Response({"error": "Invalid year_level"})

#         term_obj = Term.objects.filter(year=school_year_obj).first()
#         if not term_obj:
#             return Response({"error": "No term found for given school_year"})

#         any_error = False
#         errors = []     
#         success = []   
#         for group in data.get("data", []):
#             teacher_id = group.get("teacher_id")
#             subject_id = group.get("subject_id")

#             try:
#                 teacher_obj = Teacher.objects.get(id=teacher_id)
#                 subject_obj = Subject.objects.get(id=subject_id)
#             except (Teacher.DoesNotExist, Subject.DoesNotExist):
#                 any_error = True
#                 errors.append(f"Invalid teacher ({teacher_id}) or subject ({subject_id})")
#                 continue

#             if is_teacher:
#                 if teacher.id != teacher_obj.id:
#                     errors.append(f"Teacher mismatch: you are not allowed to submit for teacher ID {teacher_obj.id}")
#                     any_error = True
#                     continue
#                 if year_level_obj.id not in assigned_class_ids:
#                     errors.append(f"Teacher not assigned to year_level ID {year_level_obj.id}")
#                     any_error = True
#                     continue

#             for student_data in group.get("student_marks", []):
#                 student_id = student_data.get("student_id")
#                 marks = student_data.get("marks")

#                 try:
#                     student_yl = StudentYearLevel.objects.get(id=student_id, level=year_level_obj)
#                 except StudentYearLevel.DoesNotExist:
#                     errors.append(f"Student ID {student_id} not found in year_level {year_level_id}")
#                     any_error = True
#                     continue

#                 try:
#                     obj, created = StudentMarks.objects.get_or_create(
#                         student=student_yl,
#                         exam_type=exam_type_obj,
#                         term=term_obj,
#                         subject=subject_obj,
#                         teacher=teacher_obj,
#                         defaults={"marks_obtained": marks}
                        
#                     )
#                     # print("Created:", created)
#                     # print("Student:", student_id, "Subject:", subject_obj.subject_name, "Exists:", not created)

#                     if created:
#                         success.append(student_id)
#                     else:
#                         errors.append(f"Marks already exist for student {student_id} in subject {subject_obj.subject_name}")
#                         any_error = True
#                 except Exception as e:
#                     errors.append(f"Unexpected error for student {student_id}: {str(e)}")
#                     any_error = True

#         # print("Full request data:", data)
#         # print("Errors encountered:", errors)

#         if any_error:
#             return Response({
#                 "message": "Some marks could not be inserted. Either already exist or invalid data.",
#                 "errors": errors
#             }, status=400)

#         return Response({
#             "message": "Marks inserted successfully.",
#             "inserted_student_ids": success
#         }, status=201)




#     @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated], url_path='update_marks')
#     def update_marks(self, request):
#         user = request.user
#         role_names = [role.name.lower() for role in user.role.all()]

#         is_director = "director" in role_names
#         is_teacher = "teacher" in role_names

#         if not (is_director or is_teacher):
#             return Response({"error": "You do not have permission to perform this action."}, status=403)

#         data = request.data.get("data", [])
#         school_year_id = request.data.get("school_year_id")
#         exam_type_id = request.data.get("exam_type_id")
#         year_level_id = request.data.get("year_level_id")

#         errors = []
#         updated_ids = []

#         try:
#             school_year = SchoolYear.objects.get(id=school_year_id)
#             exam_type = ExamType.objects.get(id=exam_type_id)
#             term = Term.objects.filter(year=school_year).first()

#             if not term:
#                 return Response({"error": f"No term found for school year {school_year_id}"})

#         except Exception as e:
#             return Response({"error": str(e)}, status=400)

#         for item in data:
#             subject_id = item.get("subject_id")
#             try:
#                 subject = Subject.objects.get(id=subject_id)
#             except Subject.DoesNotExist:
#                 errors.append(f"Subject not found with id {subject_id}")
#                 continue

#             for student_data in item.get("student_marks", []):
#                 student_id = student_data.get("student_id")
#                 marks = student_data.get("marks")

#                 try:
#                     student = StudentYearLevel.objects.get(student__id=student_id, level_id=year_level_id)

#                     student_mark = StudentMarks.objects.filter(
#                         student=student,
#                         subject=subject,
#                         exam_type=exam_type,
#                         term=term
#                     ).first()

#                     if not student_mark:
#                         errors.append(f"Marks not found for student {student_id}, subject {subject_id}")
#                         continue

#                     student_mark.marks_obtained = marks
#                     student_mark.save()
#                     updated_ids.append(student_id)

#                 except StudentYearLevel.DoesNotExist:
#                     errors.append(f"StudentYearLevel not found for student {student_id}")
#                 except Exception as e:
#                     errors.append(f"Error updating student {student_id}: {str(e)}")

#         if errors:
#             return Response({
#                 "message": "Some marks could not be updated.",
#                 "errors": errors
#             }, status=400)

#         return Response({
#             "message": "Marks updated successfully.",
#             "updated": updated_ids
#         },status=200)


"""-------------------------------------------RESULT---------------------------------------------------"""
# from rest_framework.exceptions import PermissionDenied
# from collections import defaultdict
# from director.permission import RoleBasedPermission

# class PersonalSocialQualityView(viewsets.ModelViewSet):
#     queryset = PersonalSocialQuality.objects.all()
#     serializer_class = PersonalSocialQualitySerializer
#     permission_classes = [IsAuthenticated,IsDirectororOfficeStaff]

# class PersonalSocialGradeViewSet(viewsets.ModelViewSet):
#     queryset = PersonalSocialQualityTermWise.objects.all()
#     serializer_class = PersonalSocialGradeSerializer
#     permission_classes = [IsAuthenticated]

#     def _save_grade(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)

#     def _can_teacher_access_report_card(self, teacher, report_card_id):
#         if not teacher.year_levels.exists():
#             raise PermissionDenied("You are not assigned to any classes.")
#         return ReportCard.objects.filter(
#             id=report_card_id,
#             student_level__level__in=teacher.year_levels.all()
#         ).exists()

#     def get_queryset(self):
#         user = self.request.user
#         roles = [role.name for role in user.role.all()]
#         student_id = self.request.query_params.get("student_id")

#         qs = PersonalSocialQualityTermWise.objects.all()

#         if "office_staff" in roles or "director" in roles:
#             if student_id:
#                 qs = qs.filter(report_card__student_level__student__id=student_id)
#             return qs

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             if not teacher:
#                 return PersonalSocialQualityTermWise.objects.none()

#             if not teacher.year_levels.exists():
#                 raise PermissionDenied("You are not assigned to any classes.")

#             qs = qs.filter(
#                 report_card__student_level__level__in=teacher.year_levels.all()
#             )

#             if student_id:
#                 qs = qs.filter(report_card__student_level__student__id=student_id)

#             return qs

#         return PersonalSocialQualityTermWise.objects.none()

#     def create(self, request, *args, **kwargs):
#         user = request.user
#         roles = [role.name for role in user.role.all()]

#         if "office_staff" in roles or "director" in roles:
#             return self._save_grade(request)

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             report_card_id = request.data.get("report_card")

#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)
#             if not report_card_id:
#                 return Response({"error": "report_card ID is required"}, status=400)

#             if self._can_teacher_access_report_card(teacher, report_card_id):
#                 return self._save_grade(request)
#             else:
#                 return Response(
#                     {"error": "You're not authorized to add grades for this report card."},
#                     status=403
#                 )

#         return Response({"error": "Not allowed for your role."}, status=403)

#     def update(self, request, *args, **kwargs):
#         user = request.user
#         roles = [role.name for role in user.role.all()]
#         instance = self.get_object()

#         if "office_staff" in roles or "director" in roles:
#             return super().update(request, *args, **kwargs)

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)

#             report_card = instance.report_card
#             if report_card.student_level.level in teacher.year_levels.all():
#                 return super().update(request, *args, **kwargs)
#             else:
#                 return Response(
#                     {"error": "Not authorized to update this grade."}, status=403
#                 )

#         return Response({"error": "Not allowed for your role."}, status=403)

#     def destroy(self, request, *args, **kwargs):
#         user = request.user
#         roles = [role.name for role in user.role.all()]
#         instance = self.get_object()

#         if "office_staff" in roles or "director" in roles:
#             return super().destroy(request, *args, **kwargs)

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)

#             report_card = instance.report_card
#             if report_card.student_level.level in teacher.year_levels.all():
#                 return super().destroy(request, *args, **kwargs)
#             else:
#                 return Response(
#                     {"error": "Not authorized to delete this grade."}, status=403
#                 )

#         return Response({"error": "Not allowed for your role."}, status=403)

# class NonScholasticGradeViewSet(viewsets.ModelViewSet):
#     queryset = NonScholasticGradeTermWise.objects.all()
#     serializer_class = NonScholasticGradeTermWiseSerializer
#     permission_classes = [IsAuthenticated]

#     def _save_grade(self, request):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(serializer.data)

#     def _can_teacher_access_report_card(self, teacher, report_card_id):
#         return ReportCard.objects.filter(
#             id=report_card_id,
#             student_level__level__in=teacher.year_levels.all()
#         ).exists()
    
#     def get_queryset(self):
#         user = self.request.user
#         roles = [role.name for role in user.role.all()]
#         # print("role:",roles)
#         student_id = self.request.query_params.get("student_id")

#         if "office_staff" in roles or "director" in roles:
#             qs = NonScholasticGradeTermWise.objects.all()
#             if student_id:
#                 qs = qs.filter(report_card__student_level__student__id=student_id)
#             return qs

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             if not teacher:
#                 return PersonalSocialQualityTermWise.objects.none()

#             if not teacher.year_levels.exists():
#                 raise PermissionDenied("You are not assigned to any classes.")

#             qs = qs.filter(
#                 report_card__student_level__level__in=teacher.year_levels.all()
#             )

#             if student_id:
#                 qs = qs.filter(report_card__student_level__student__id=student_id)

#             return qs


#         return NonScholasticGradeTermWise.objects.none()

#     def create(self, request, *args, **kwargs):
#         user = request.user
#         roles = [role.name for role in user.role.all()]

#         if "office_staff" in roles or "director" in roles:
#             return self._save_grade(request)

#         elif "teacher" in roles:
#             teacher = getattr(user, "teacher", None)
#             report_card_id = request.data.get("report_card")

#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)
#             if not report_card_id:
#                 return Response({"error": "report_card ID is required"}, status=400)

#             if self._can_teacher_access_report_card(teacher, report_card_id):
#                 return self._save_grade(request)
#             else:
#                 return Response({"error": "You're not authorized to add grades for this report card."}, status=403)

#         return Response({"error": "Not allowed for your role."}, status=403)

#     def update(self, request, *args, **kwargs):
#         user = request.user
#         roles =[role.name for role in user.role.all()]

#         instance = self.get_object()

#         if "office_staff" in roles or "director" in roles:
#             return super().update(request, *args, **kwargs)

#         elif "teacher" in roles:
#             teacher = user.teacher
#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)

#             report_card = instance.report_card
#             if report_card.student_level.level in teacher.year_levels.all():
#                 return super().update(request, *args, **kwargs)
#             else:
#                 return Response({"error": "Not authorized to update this grade."}, status=403)

#         return Response({"error": "Not allowed for your role."}, status=403)

#     def destroy(self, request, *args, **kwargs):
#         user = request.user
#         roles = [role.name for role in user.role.all()]

#         instance = self.get_object()

#         if "office_staff" in roles or "director" in roles:
#             return super().destroy(request, *args, **kwargs)

#         elif "teacher" in roles:
#             teacher = user.teacher
#             if not teacher:
#                 return Response({"error": "Teacher profile not found."}, status=400)

#             report_card = instance.report_card
#             if report_card.student_level.level in teacher.year_levels.all():
#                 return super().destroy(request, *args, **kwargs)
#             else:
#                 return Response({"error": "Not authorized to delete this grade."}, status=403)

#         return Response({"error": "Not allowed for your role."}, status=403)
    
#     @action(detail=False, methods=["get"], url_path="non_schl_subject")
#     def get_non_scholastic_subject(self, request):
#         subjects = Subject.objects.filter(department__department_name__iexact="Non-Scholastic")
#         serializer = subjectSerializer(subjects, many=True)
#         return Response(serializer.data) 

# class ReportCardViewSet(viewsets.ModelViewSet):
#     queryset = ReportCard.objects.all()
#     serializer_class = ReportCardSerializer
#     permission_classes = [IsAuthenticated, RoleBasedPermission]

#     def get_user_roles(self):
#         user = self.request.user
#         return [role.name for role in user.role.all()]

#     def get_queryset(self):
#         user = self.request.user
#         roles = self.get_user_roles()

#         student_id = self.request.query_params.get('student_id')
#         standard_filter = self.request.query_params.get('standard')
#         division_filter = self.request.query_params.get('division')

#         if student_id:
#             return self.queryset.filter(student_level__student__id=student_id)

#         if standard_filter:
#             return self.queryset.filter(student_level__level__level_name=standard_filter)
        
#         if division_filter:
#             return self.queryset.filter(report_card__division=division_filter)


#         if 'director' in roles or 'office staff' in roles:
#             return self.queryset

#         if 'teacher' in roles:
#             try:
#                 teacher = user.teacher
#                 return self.queryset.filter(
#                     student_level__level__in=teacher.year_levels.all()
#                 )
#             except Teacher.DoesNotExist:
#                 return self.queryset.none()

#         if 'guardian' in roles:
#             student_ids = StudentGuardian.objects.filter(
#                 guardian__user=user
#             ).values_list('student_id', flat=True)
#             return self.queryset.filter(student_level__student__id__in=student_ids)

#         if 'student' in roles:
#             return self.queryset.filter(student_level__student__user=user)

#         return self.queryset.none()


#     def get_attendance_string(self, report_card):
#         student_level = report_card.student_level
#         attendance_qs = StudentAttendance.objects.filter(student=student_level.student)
#         present = attendance_qs.filter(status='P').count()
#         total = 230
#         attendance= f"{present}/{total}" 
#         return attendance

#     def get_promoted_class(self, report_card):
#         # division = report_card.division
#         sup = report_card.supplementary_in
#         failed_subjects = [s.strip() for s in ( sup or "").split(",") if s.strip()]
        
#         if failed_subjects:
#             return None
        
#         # if division=="Fail":
#         #     return None
            
#         current_level = report_card.student_level.level
#         current_year = report_card.student_level.year
#         student = report_card.student_level.student

#         # Try getting the next level
#         next_level = YearLevel.objects.filter(level_order=current_level.level_order + 1).first()
#         if not next_level:

#             return None  # Already in the highest class
        
#         next_year = SchoolYear.objects.filter(start_date__gt=current_year.start_date).order_by('start_date').first()
#         if not current_year or not current_year.start_date:
#             return None

        
#         # Get or create the corresponding StudentYearLevel for next class in same year
#         promoted_to, _ = StudentYearLevel.objects.get_or_create(
#             student=student,
#             level=next_level,
#             year=next_year # or next academic year if needed
#         )
#         return promoted_to 

#     def get_document(self, report_card):
#         documents_data = []

#         for doc_rel in report_card.documents.select_related("documents").all():
#             document = doc_rel.documents
#             if document:
#                 doc_types = list(document.document_types.values_list("name", flat=True))
#                 documents_data.append({
#                     "identities": document.identities,
#                     "document_types": doc_types
#                 })

#         return documents_data

#     def get_non_scholastic_data(self,report_card):
#         return [
#             {
#                 "subject": item.non_scholastic_subject.subject_name,
#                 "term": f"Term {item.term.term_number}",
#                 "grade": item.grade
#             }
#             for item in report_card.non_scholastic_grades.select_related("term", "non_scholastic_subject")
#         ]
        
#     def get_subject_score(self, report_card):
#         from collections import defaultdict

#         # Step 1: Get the StudentYearLevel linked to the report card
#         student_level = report_card.student_level  # THIS is a StudentYearLevel instance

#         # Step 2: Fetch all marks linked to that student_level
#         marks_qs = StudentMarks.objects.select_related(
#             "exam_type", "subject", "term", "student"
#         ).filter(student=student_level)  # must pass StudentYearLevel instance

#         if not marks_qs.exists():
#             return []

#         # Step 3: Group marks by exam type and subject
#         temp = defaultdict(dict)
#         for mark in marks_qs:
#             exam_type = mark.exam_type.name.lower()
#             subject = mark.subject.subject_name
#             temp[exam_type][subject] = float(mark.marks_obtained or 0)

#         # Step 4: Compute totals + grades
#         examwise_summary = []
#         for exam_type, subjects in temp.items():
#             subject_count = len(subjects)
#             is_fa = exam_type.startswith("fa")  # FA1/FA2 -> 10 marks per subject
#             max_per_subject = 10 if is_fa else 100
#             total_obtained = sum(subjects.values())
#             total_possible = subject_count * max_per_subject
#             percentage = round((total_obtained / total_possible) * 100, 2) if total_possible else 0

#             #  Add grading logic
#             if percentage >= 90:
#                 grade = "A+"
#             elif percentage >= 75:
#                 grade = "A"
#             elif percentage >= 60:
#                 grade = "B"
#             elif percentage >= 50:
#                 grade = "C"
#             elif percentage >= 40:
#                 grade = "D"
#             else:
#                 grade = "F"

#             examwise_summary.append({
#                 "exam_type": exam_type.upper(),
#                 "subjects": subjects,
#                 "total_obtained": total_obtained,
#                 "total_possible": total_possible,
#                 "percentage": percentage,
#                 "grade": grade
#             })

#         return examwise_summary


#     def sync_subject_scores(self, report_card):
#         terms = Term.objects.filter(year=report_card.student_level.year)

#         student_marks = StudentMarks.objects.filter(
#             student=report_card.student_level,
#             term__in=terms
#         )
#         for mark in student_marks:
#             SubjectScore.objects.get_or_create(report_card=report_card, marks_obtained=mark)
    
#     def save_documents(self, report_card):
#         student = report_card.student_level.student
#         student_docs = Document.objects.filter(
#             student=student,
#             document_types__isnull=False
#         ).distinct()

#         for doc in student_docs:
#             # Only link if not already linked
#             if not ReportCardDocument.objects.filter(report_card=report_card, documents=doc).exists():
#                 ReportCardDocument.objects.create(report_card=report_card, documents=doc)

#     def save_subject_scores(self, report_card, subjects_data):
#         for subject_data in subjects_data:
#             subject_name = subject_data.get("subject")
#             if not subject_name:
#                 continue
#             subject = Subject.objects.get(subject_name=subject_name)
#             for exam_key in ["fa1", "fa2", "fa3", "sa1", "sa2", "sa3"]:
#                 marks = subject_data.get(exam_key)
#                 if marks is not None:
#                     exam_type = ExamType.objects.get(name__iexact=exam_key.upper())
#                     term = Term.objects.filter(year=report_card.student_level.year.year_name).first()
#                     student_marks = StudentMarks.objects.create(
#                         exam_type=exam_type,
#                         subject=subject,
#                         term=term,
#                         student=report_card.student_level.student,
#                         teacher=Teacher.objects.first(),
#                         marks_obtained=marks
#                     )
#                     SubjectScore.objects.create(
#                         report_card=report_card,
#                         marks_obtained=student_marks
#                     )
#                     # print("RC ID", report_card.id)  

#     def save_non_scholastic(self, report_card, grades):
#         for subject_name, values in grades.items():
#             subject = Subject.objects.get(subject_name=subject_name)
#             for term_key, grade in values.items():
#                 term = Term.objects.get(name__iexact=term_key)
#                 NonScholasticGradeTermWise.objects.create(
#                     report_card=report_card,
#                     non_scholastic_subject=subject,
#                     term=term,
#                     grade=grade
#                 )

#     def save_personal_social(self, report_card, data):
#         all_qualities = PersonalSocialQuality.objects.all()
#         for term_key, quality_dict in data.items():
#             term_number = 1 if term_key == "Term 1" else 2
#             term = Term.objects.get(term_number=term_number, year=report_card.student_level.year)
#             for quality in all_qualities:
#                 grade = quality_dict.get(quality.quality_name)
#                 if grade:
#                     NonScholasticGradeTermWise.objects.create(
#                         report_card=report_card,
#                         personal_quality=quality,
#                         term=term,
#                         grade=grade
#                     )



#     def create(self, request, *args, **kwargs):
#         roles = self.get_user_roles()
#         if 'director' not in roles:
#             if 'teacher' in roles:
#                 teacher = getattr(request.user, 'teacher', None)
#                 student_level_id = request.data.get("student_level")
#                 if teacher and student_level_id:
#                     try:
#                         student_level = StudentYearLevel.objects.get(id=student_level_id)
#                         if student_level.level not in teacher.year_levels.all():
#                             return Response({"error": "Permission denied."}, status=403)
#                     except StudentYearLevel.DoesNotExist:
#                         return Response({"error": "Invalid student_level ID."}, status=400)
#                 else:
#                     return Response({"error": "Permission denied."}, status=403)
#             else:
#                 return Response({"error": "Permission denied."}, status=403)
            
#         data = request.data.copy()
#         student_level = StudentYearLevel.objects.get(id=data.get("student_level"))
#         student = student_level.student
#         academic_year = student_level.year
#         student_level = StudentYearLevel.objects.get(student=student, year=academic_year)

#         existing = ReportCard.objects.filter(student_level=student_level).first()
#         if existing:
#             return Response(
#                 {"error": "Report card for this student and academic year already exists."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )

#         # STEP 1: Create report_card first with temporary placeholder values
#         report_card = ReportCard.objects.create(
#             student_level=student_level,
#             total_marks=0,
#             max_marks=0,
#             percentage=0.0,
#             grade="F",
#             division="Fail",
#             rank=data.get("rank"),
#             attendance=None,
#             supplementary_in = [],
#             teacher_remark=data.get("teacher_remark"),
#             promoted_to_class= None,#self.get_promoted_class(ReportCard),  
#             school_reopen_date=parse_date(data.get("school_reopen_date"))
#         )

#         # STEP 2: Save related data (required for subject score calc)
#         self.save_documents(report_card)
#         self.save_subject_scores(report_card, data.get("subjects", []))
#         self.save_non_scholastic(report_card, data.get("non_scholastic", {}))
#         self.save_personal_social(report_card, data.get("personal_social", {}))

#         # STEP 3: Sync marks to SubjectScore and recalculate
#         self.sync_subject_scores(report_card)
#         subjects = self.get_subject_score(report_card)
#         subject_avg = calculate_subject_summary(subjects)

#         total_obtained = subject_avg["total_marks"]
#         total_possible = subject_avg["max_marks"]
#         percentage = subject_avg["percentage"]
#         grade = subject_avg["grade"]
#         supplementary_in = ", ".join(subject_avg["supplementary_in"]) if subject_avg["supplementary_in"] else ""

#         if percentage >= 60:
#             division = "First"
#         elif percentage >= 50:
#             division = "Second"
#         elif percentage >= 40:
#             division = "Third"
#         else:
#             division = "Fail"

#         # STEP 4: Save final calculated fields
#         report_card.attendance = self.get_attendance_string(report_card)
#         report_card.total_marks = total_obtained
#         report_card.max_marks = total_possible
#         report_card.percentage = percentage
#         report_card.grade = grade
#         report_card.division = division
#         report_card.supplementary_in = supplementary_in
#         report_card.promoted_to_class = self.get_promoted_class(report_card)
        
#         report_card.save()

#         return Response(self.build_report_card_response(report_card), status=status.HTTP_201_CREATED)
    
#     def build_report_card_response(self, report_card):
#         student = report_card.student_level.student
#         user = student.user
        
#         self.sync_subject_scores(report_card)
#         subjects = self.get_subject_score(report_card)

#         subject_avg = calculate_subject_summary(subjects)

#         total_obtained = subject_avg["total_marks"]
#         total_possible = subject_avg["max_marks"]
#         percentage = subject_avg["percentage"]
#         grade = subject_avg["grade"]
#         supplementary_in = subject_avg["supplementary_in"]

#         if percentage >= 60:
#             division = "First"
#         elif percentage >= 50:
#             division = "Second"
#         elif percentage >= 40:
#             division = "Third"
#         else:
#             division = "Fail"


#         documents_list = []

#         for doc_link in report_card.documents.select_related("documents").all():
#             doc = doc_link.documents
#             if doc and doc.document_types.exists():
#                 try:
#                     # Force identities into list if stored as a string
#                     identities = doc.identities
#                     if isinstance(identities, str):
#                         identities = json.loads(identities)

#                     if not isinstance(identities, list):
#                         identities = [identities]

#                     for doc_type in doc.document_types.all():
#                         documents_list.append({doc_type.name: identities[0] if identities else None})

#                 except Exception as e:
#                     # fallback when json.loads fails
#                     print("Error parsing identities:", e)
#                     continue

                    
#         non_scholastic = {}
#         for ns_grade in report_card.non_scholastic_grades.select_related("non_scholastic_subject", "term"):
#             subject = ns_grade.non_scholastic_subject.subject_name
#             term = f"Term {ns_grade.term.term_number}"
#             if subject not in non_scholastic:
#                 non_scholastic[subject] = {}
#             non_scholastic[subject][term] = ns_grade.grade

#         personal_social = [
#             {
#                 "quality": psq.personal_quality.quality_name,
#                 "term": f"Term {psq.term.term_number}",
#                 "grade": psq.grade
#             }
#             for psq in report_card.personal_qualities.select_related("personal_quality", "term")
#         ]

#         full_name = " ".join(filter(None, [user.first_name, user.middle_name, user.last_name]))

#         return {
#             "id": report_card.id,
#             "student": student.id,
#             "student_name": full_name,
#             "father_name": student.father_name,
#             "mother_name": student.mother_name,
#             "date_of_birth": student.date_of_birth,
#             "contact_number": student.contact_number,
#             "scholar_number": student.scholar_number,
#             "standard": report_card.student_level.level.level_name,
#             "academic_year": report_card.student_level.year.year_name,
#             "total_marks": total_obtained,
#             "max_marks": total_possible,
#             "percentage": percentage,
#             "grade": grade,
#             "division": division,
#             "rank": report_card.rank,
#             "attendance": self.get_attendance_string(report_card),
#             "teacher_remark": report_card.teacher_remark,
#             "supplementary_in": supplementary_in,
#             "promoted_to_class": (report_card.promoted_to_class.level.level_name 
#                 if report_card.promoted_to_class and report_card.promoted_to_class.level 
#                 else None),
#             "school_reopen_date": report_card.school_reopen_date,
#             "documents": documents_list,
#             "subjects": self.get_subject_score(report_card),
#             "subject_avg": subject_avg["subject_avg"],
#             "non_scholastic": self.get_non_scholastic_data(report_card),
#             "personal_social": personal_social,

#         } 

#     def retrieve(self, request, *args, **kwargs):
#         report_card = self.get_object()
#         data = self.build_report_card_response(report_card)
#         return Response(data)

#     def list(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         return Response([self.build_report_card_response(rc) for rc in queryset])

#     def update(self, request, *args, **kwargs):
#         roles = self.get_user_roles()
#         if 'director' not in roles:
#             if 'teacher' in roles:
#                 teacher = getattr(request.user, 'teacher', None)
#                 instance = self.get_object()
#                 if not teacher or instance.student_level.level not in teacher.year_levels.all():
#                     return Response({"error": "Permission denied."}, status=403)
#             else:
#                 return Response({"error": "Permission denied."}, status=403)
            
#         partial = kwargs.pop("partial", False)
#         instance = self.get_object()
#         data = request.data

#         instance.total_marks = data.get("total_marks", instance.total_marks)
#         instance.max_marks = data.get("max_marks", instance.max_marks)
#         instance.percentage = data.get("percentage", instance.percentage)
#         instance.grade = data.get("grade", instance.grade)
#         instance.division = data.get("division", instance.division)
#         instance.rank = data.get("rank", instance.rank)
#         instance.attendance = data.get("attendance", instance.attendance)
#         instance.teacher_remark = data.get("teacher_remark", instance.teacher_remark)
#         instance.supplementary_in = data.get("supplementary_in", instance.supplementary_in)
#         instance.school_reopen_date = data.get("school_reopen_date", instance.school_reopen_date)

#         promoted_id = data.get("promoted_to_class")
#         if promoted_id:
#             instance.promoted_to_class_id = promoted_id

#         instance.save()

#         subjects_data = data.get("subjects", [])
#         if subjects_data:
#             instance.subject_scores.all().delete()
#             for sub in subjects_data:
#                 subject_name = sub.get("subject")
#                 exam_type = sub.get("exam_type")
#                 marks = sub.get("marks")
#                 try:
#                     subject_obj = Subject.objects.get(subject_name=subject_name)
#                     exam_type_obj = ExamType.objects.get(name=exam_type)
#                     student_mark = StudentMarks.objects.create(
#                         student=instance.student,
#                         subject=subject_obj,
#                         exam_type=exam_type_obj,
#                         marks_obtained=marks,
#                         term=Term.objects.filter(year=instance.academic_year.year).first()
#                     )
#                     SubjectScore.objects.create(report_card=instance, marks_obtained=student_mark)
#                 except Exception as e:
#                     print("Subject Update Error:", e)


#         documents_data = data.get("documents", {})
#         if documents_data:
#             # Clear existing linked documents
#             instance.documents.all().delete()

#             #  Fetch all documents related to the same student
#             student_docs = Document.objects.filter(student=instance.student_level.student)

#             #  Link all of them to the report card
#             for doc in student_docs:
#                 ReportCardDocument.objects.create(
#                     report_card=instance,
#                     documents=doc
#                 )


#         non_scholastic_data = data.get("non_scholastic", {})
#         if non_scholastic_data:
#             instance.non_scholastic_grades.all().delete()
#             for subject_name, terms in non_scholastic_data.items():
#                 subject_obj = Subject.objects.get(subject_name=subject_name)
#                 for term_name, grade in terms.items():
#                     term_obj = Term.objects.get(term_number=term_name)
#                     NonScholasticGradeTermWise.objects.create(
#                         report_card=instance,
#                         non_scholastic_subject=subject_obj,
#                         term=term_obj,
#                         grade=grade
#                     )

#         personal_data = data.get("personal_social", [])
#         if personal_data:
#             instance.personal_qualities.all().delete()
#             for item in personal_data:
#                 quality = item.get("quality")
#                 term = item.get("term")
#                 grade = item.get("grade")
#                 try:
#                     quality_obj = PersonalSocialQuality.objects.get(quality_name=quality)
#                     term_obj = Term.objects.get(term_number=term)
#                     PersonalSocialQualityTermWise.objects.create(
#                         report_card=instance,
#                         personal_quality=quality_obj,
#                         term=term_obj,
#                         grade=grade
#                     )
#                 except Exception as e:
#                     print("PSQ Update Error:", e)

#         return self.retrieve(request, *args, **kwargs)

class ReportCardView(viewsets.ModelViewSet):
    queryset = ReportCard.objects.all()
    serializer_class = ReportCardSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        # Validate strictly so serializer.errors are populated and returned when input is invalid
        serializer.is_valid(raise_exception=True)

        student = serializer.validated_data.get('student')
        file = serializer.validated_data.get('file')

        if not student:
            return Response({"error": "Student must be provided."}, status=400)
        if not file:
            return Response({"error": "ReportCard file must be provided."}, status=400)
        if ReportCard.objects.filter(student=student).exists():
            return Response(
                {"error": f"ReportCard for {student} in this year level already exists."},
                status=400
            )

        self.perform_create(serializer)
        return Response(serializer.data, status=201)

    def to_representation(self, instance):
        """Return a compact representation for a ReportCard instance.

        Format:
        {
            "id": <int>,
            "file": <absolute url or None>,
            "student": <student full name or None>,
            "year_level": <level_name or None>
        }
        """
        # id
        data = {"id": getattr(instance, "id", None)}

        # file URL (prefer absolute URL using request if available). If not present, return a clear message.
        file_field = getattr(instance, "file", None)
        file_url = None
        if file_field:
            try:
                url = file_field.url
            except Exception:
                url = None

            if url:
                try:
                    request = getattr(self, "request", None)
                    # If file is claimed by the FileField, ensure it actually exists on disk
                    file_path = getattr(file_field, 'path', None)
                    file_exists = False
                    try:
                        if file_path and os.path.exists(file_path):
                            file_exists = True
                    except Exception:
                        file_exists = False

                    if request:
                        built_url = request.build_absolute_uri(url)
                    else:
                        built_url = url

                    if file_exists:
                        file_url = built_url
                    else:
                        # File record exists but file missing on server
                        file_url = None
                except Exception:
                    file_url = url

        # provide a visible message when file isn't attached or missing on disk
        if not file_field:
            data["file"] = "No file attached"
        else:
            # file_field exists but file_url is None when missing on disk
            if not file_url:
                data["file"] = "File missing on server"
            else:
                data["file"] = file_url

        # student name (StudentYearLevel -> Student -> User)
        student_yl = getattr(instance, "student", None)
        student_name = None
        year_level_name = None
        try:
            if student_yl and getattr(student_yl, "student", None):
                user = getattr(student_yl.student, "user", None)
                if user:
                    parts = [getattr(user, "first_name", ""), getattr(user, "middle_name", ""), getattr(user, "last_name", "")]
                    student_name = " ".join([p for p in parts if p]).strip() or None

            if student_yl and getattr(student_yl, "level", None):
                year_level_name = getattr(student_yl.level, "level_name", None)
        except Exception:
            student_name = student_name or None
            year_level_name = year_level_name or None

        data["student"] = student_name
        data["year_level"] = year_level_name

        return data

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.to_representation(instance))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            data = [self.to_representation(obj) for obj in page]
            return self.get_paginated_response(data)

        data = [self.to_representation(obj) for obj in queryset]
        return Response(data)

# ---------------------Expense 

class PaymentView(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

class ExpenseCategoryView(viewsets.ModelViewSet):
    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [IsAuthenticated, ExpensePermission]

def get_current_school_year():
    today = date.today()
    return SchoolYear.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).first()

class SchoolExpenseView(viewsets.ModelViewSet):
    queryset = SchoolExpense.objects.select_related("payment", "category", "school_year")
    serializer_class = SchoolExpenseSerializer
    permission_classes = [IsAuthenticated, ExpensePermission]

    def create(self, request, *args, **kwargs):
        data = request.data.copy()

        # ---------------------------------------------------------
        # 1. SALARY CATEGORY CHECK
        # ---------------------------------------------------------

        #payload for salary expense
        '''
        {
            "school_year": 1,
            "category": 2,
            "month": "December"
        }
        '''

        salary_category = ExpenseCategory.objects.filter(name__iexact="salary").first()
        selected_category = ExpenseCategory.objects.get(id=data.get("category"))

        if selected_category == salary_category:

            # Disallow manual amount / payment input
            if "payment" in data or "amount" in data:
                return Response({
                    "error": "You cannot provide amount or payment for Salary category. It is auto-calculated."
                }, status=400)

            # -----------------------------------------------------
            # choose month
            # -----------------------------------------------------
            requested_month = data.get("month")

            MONTHS = [
                "January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"
            ]

            if not requested_month or requested_month not in MONTHS:
                return Response({
                    "error": "Invalid or missing month. Allowed: " + ", ".join(MONTHS)
                }, status=400)

            current_month = requested_month
            school_year = data.get("school_year")

            # Fetch employee salaries
            salaries = EmployeeSalary.objects.filter(
                month=current_month,
                school_year=school_year
            )

            # -----------------------------------------------------
            # Salary totals
            # -----------------------------------------------------
            total_salary = salaries.aggregate(total=models.Sum("net_amount"))["total"] or 0

            cash_paid = salaries.filter(payment__payment_method="Cash").aggregate(
                t=models.Sum("net_amount")
            )["t"] or 0

            cheque_paid = salaries.filter(payment__payment_method="Cheque").aggregate(
                t=models.Sum("net_amount")
            )["t"] or 0

            online_paid = salaries.filter(payment__payment_method="Online").aggregate(
                t=models.Sum("net_amount")
            )["t"] or 0

            summary_text = (
                f"Salary Expense for {current_month}\n\n"
                f"Total Salary: ₹{total_salary}\n"
                f"Cash Paid: ₹{cash_paid}\n"
                f"Cheque Paid: ₹{cheque_paid}\n"
                f"Online Paid: ₹{online_paid}"
            )


            # -----------------------------------------------------
            # Create salary expense (NO PAYMENT OBJECT)
            # -----------------------------------------------------
            expense = SchoolExpense.objects.create(
                category=salary_category,
                school_year_id=school_year,
                description=summary_text,
                created_by=request.user,
                approved_by=request.user,
                payment=None,            #  no Payment model used
            )

            return Response({
                "message": "Salary expense created automatically",
                "month": current_month,
                "expense_id": expense.id,
                "expense": SchoolExpenseSerializer(expense).data
            }, status=201)


        # ---------------------------------------------------------
        # 2. NORMAL EXPENSE CREATION 
        # ---------------------------------------------------------
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        payment_method = serializer.validated_data["payment"]["payment_method"]
        payment_data = serializer.validated_data["payment"]

        # Save payment
        payment = Payment.objects.create(**payment_data)

        # Create expense
        expense = SchoolExpense.objects.create(
            category=serializer.validated_data["category"],
            school_year=serializer.validated_data["school_year"],
            description=serializer.validated_data.get("description"),
            created_by=request.user,
            payment=payment,
        )

        # OG LOGIC REBUILT PROPERLY
        if payment_method.lower() == "cash":
            payment.status = "Success"
            expense.approved_by = request.user
            payment.save()
            expense.save()
            return Response({
                "message": "Expense approved successfully (Cash)",
                "expense": SchoolExpenseSerializer(expense).data
            })

        elif payment_method.lower() == "cheque":
            payment.status = "Pending"
            payment.save()
            return Response({
                "message": "Cheque expense created, pending approval",
                "expense": SchoolExpenseSerializer(expense).data
            })

        elif payment_method.lower() == "online":
            payment.status = "Success"
            expense.approved_by = request.user
            payment.save()
            expense.save()
            return Response({
                "message": "Expense approved successfully (Online)",
                "expense": SchoolExpenseSerializer(expense).data
            })

        return Response({"error": "Invalid payment method"}, status=400)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        data = request.data.copy()

        # Detect SALARY category expense
        if instance.category.name.lower() == "salary":

            # which month? from PATCH body OR fallback from description
            month = data.get("month")

            if not month:
                # fallback: extract month from description
                first_line = instance.description.split("\n")[0]  # "Salary Expense for December"
                month = first_line.replace("Salary Expense for ", "").strip()

            # Fetch updated salary records
            salaries = EmployeeSalary.objects.filter(
                month=month,
                school_year=instance.school_year
            )

            if not salaries.exists():
                return Response({
                    "error": f"No employee salary records found for {month}."
                }, status=400)

            total_salary = salaries.aggregate(total=models.Sum("net_amount"))["total"] or 0
            cash_paid = salaries.filter(payment__payment_method="Cash").aggregate(t=models.Sum("net_amount"))["t"] or 0
            cheque_paid = salaries.filter(payment__payment_method="Cheque").aggregate(t=models.Sum("net_amount"))["t"] or 0
            online_paid = salaries.filter(payment__payment_method="Online").aggregate(t=models.Sum("net_amount"))["t"] or 0

            # rebuild description
            new_summary = (
                f"Salary Expense for {month}\n\n"
                f"Total Salary: ₹{total_salary}\n"
                f"Cash Paid: ₹{cash_paid}\n"
                f"Cheque Paid: ₹{cheque_paid}\n"
                f"Online Paid: ₹{online_paid}"
            )

            instance.description = new_summary
            instance.save()

            return Response({
                "message": "Salary expense refreshed with latest records.",
                "expense": SchoolExpenseSerializer(instance).data
            })

        # NORMAL EXPENSE update
        return super().update(request, *args, **kwargs)



    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data, context={"request": request})
    #     serializer.is_valid(raise_exception=True)

    #     payment_method = serializer.validated_data["payment"]["payment_method"]
    #     payment_data = serializer.validated_data["payment"]

    #     # Save payment
    #     payment = Payment.objects.create(**payment_data)

    #     # Create expense
    #     expense = SchoolExpense.objects.create(
    #         category=serializer.validated_data["category"],
    #         school_year=serializer.validated_data["school_year"],
    #         description=serializer.validated_data.get("description"),
    #         created_by=request.user,
    #         payment=payment,
    #     )

    #     # OG LOGIC REBUILT PROPERLY
    #     if payment_method.lower() == "cash":
    #         payment.status = "Success"
    #         expense.approved_by = request.user
    #         payment.save()
    #         expense.save()
    #         return Response({
    #             "message": "Expense approved successfully (Cash)",
    #             "expense": SchoolExpenseSerializer(expense).data
    #         })

    #     elif payment_method.lower() == "cheque":
    #         # Cheque always stays pending until verified
    #         payment.status = "Pending"
    #         payment.save()
    #         return Response({
    #             "message": "Cheque expense created, pending approval",
    #             "expense": SchoolExpenseSerializer(expense).data
    #         })

    #     elif payment_method.lower() == "online":
    #         return Response({
    #             "message": "Use initiate-expense-payment API",
    #             "expense_id": expense.id,
    #             "payment_id": payment.id,
    #             "expense": SchoolExpenseSerializer(expense).data
    #         }, status=400)
        
    #     return Response({"error": "Invalid payment method"}, status=400)

    # @action(detail=True, methods=["post"], url_path="initiate-online-payment")
    # def initiate_expense_payment(self, request, pk=None):
    #     expense = self.get_object()
    #     payment = expense.payment

    #     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    #     order = client.order.create({
    #         "amount": int(payment.amount * 100),
    #         "currency": "INR",
    #         "receipt": f"EXP-{expense.id}",
    #         "payment_capture": "1",
    #     })

    #     payment.remarks = f"OrderID: {order['id']}"
    #     payment.save()

    #     return Response({
    #         "expense_id": expense.id,
    #         "payment_id": payment.id,
    #         "razorpay_order_id": order["id"],
    #         "razorpay_key": settings.RAZORPAY_KEY_ID,
    #         "amount": str(payment.amount),
    #     })

    # @action(detail=True, methods=["post"], url_path="confirm-online-payment")
    # def confirm_expense_payment(self, request, pk=None):
    #     expense = self.get_object()
    #     payment = expense.payment

    #     data = request.data

    #     client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    #     client.utility.verify_payment_signature({
    #         "razorpay_order_id": data["razorpay_order_id"],
    #         "razorpay_payment_id": data["razorpay_payment_id"],
    #         "razorpay_signature": data["razorpay_signature"]
    #     })

    #     # After success
    #     payment.status = "Success"
    #     payment.payment_method = "Online"
    #     payment.save()

    #     expense.approved_by = request.user
    #     expense.save()

    #     return Response({
    #         "message": "Payment confirmed!",
    #         "expense": SchoolExpenseSerializer(expense).data
    #     })




class EmployeeView(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated,EmployeePermission]

    @action(detail=False, methods=["get"], url_path="get_emp")
    def get_emp(self, request):
        role = request.query_params.get("role")
        emp_id = request.query_params.get("id")   
        name = request.query_params.get("name")
        queryset = self.get_queryset()
        filters = Q()  


        if emp_id:
            try:
                employee = Employee.objects.get(pk=emp_id)
            except Employee.DoesNotExist:
                return Response({"error": "Employee not found"}, status=404)

            serializer = EmployeeSerializer(employee)
            return Response(serializer.data)

        if role:
            role_lower = role.lower()
            if role_lower == "teacher":
                all_teachers = User.objects.filter(role__name__iexact="teacher")
                employees_users = Employee.objects.values_list('user', flat=True)
                users_to_return = all_teachers.exclude(id__in=employees_users)

            elif role_lower == "office staff":
                all_staff = User.objects.filter(role__name__iexact="office staff")
                employees_users = Employee.objects.values_list('user', flat=True)
                users_to_return = all_staff.exclude(id__in=employees_users)

            else:
                users_to_return = User.objects.none()
                
            serializer = UserSerializer(users_to_return, many=True)
            return Response(serializer.data)

        if name:
            filters &= (
                Q(user__first_name__icontains=name) |
                Q(user__middle_name__icontains=name) |
                Q(user__last_name__icontains=name)
            )
        queryset = queryset.filter(filters).distinct()

        # queryset = self.get_queryset()
        serializer = self.get_serializer(queryset.distinct(), many=True)
        return Response(serializer.data)


    @action(detail=False, methods=["post"], url_path="create_emp")
    def create_emp(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        user_id = request.data.get("user")
        if not user_id:
            return Response({"error": "Employee is required."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid employee id."}, status=400)

        roles = [r.name.lower() for r in user.role.all()]
        if not any(r in ["teacher", "office staff"] for r in roles):
            return Response(
                {"error": "Only Teacher or Office Staff can be assigned as employee."},
                status=400
            )

        if Employee.objects.filter(user=user).exists():
            return Response(f"Salary is already created for {user.first_name} {user.last_name}".strip(), status=400)

        employee = Employee.objects.create(
            user=user,
            base_salary=serializer.validated_data["base_salary"],
        )

        serializer = self.get_serializer(employee)
        return Response({"message": "Employee created successfully.", "data": serializer.data}, status=201)


    # @action(detail=False, methods=["put"], url_path="update_emp")
    def update_emp(self, request):
        user_id = request.data.get("user")
        # joining_date = request.data.get("joining_date")

        # if not user_id or not joining_date:
        #     return Response({"error": "user and joining_date are required."}, status=400)
        if not user_id :
            return Response({"error": "user are required."}, status=400)

        try:
            # employee = Employee.objects.get(user_id=user_id, joining_date=joining_date)
            employee = Employee.objects.get(user_id=user_id)

        except Employee.DoesNotExist:
            return Response({"error": "Employee not found with this user and joining_date"}, status=404)

        serializer = self.get_serializer(employee, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Employee updated successfully", "data": serializer.data})
        return Response(serializer.errors, status=400)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Employee deleted successfully"},
            status=status.HTTP_200_OK
        )



class EmployeeSalaryView(viewsets.ModelViewSet):
    queryset = EmployeeSalary.objects.all()
    serializer_class = EmployeeSalarySerializer
    permission_classes = [IsAuthenticated, ExpensePermission]
    api_section = "employee_salary"

    def get_queryset(self):
        user = self.request.user
        queryset = EmployeeSalary.objects.all()

        roles = [r.name.lower() for r in user.role.all()]
        if hasattr(user, "employee") and "director" not in roles:
            queryset = queryset.filter(user=user.employee)
        # if hasattr(user, "employee"):
        #     queryset = queryset.filter(user=user.employee)

        school_year_id = self.request.query_params.get("school_year")
        month = self.request.query_params.get("month")
        employee_id = self.request.query_params.get("user")
        status = self.request.query_params.get("status")

        if school_year_id:
            queryset = queryset.filter(school_year_id=school_year_id)
        if month:
            queryset = queryset.filter(month=month)
        if employee_id:
            queryset = queryset.filter(user_id=employee_id)
        if status:
            queryset = queryset.filter(status=status)

        return queryset


    def create(self, request, *args, **kwargs):
        employees_ids = request.data.get("employees", [])
        months = request.data.get("months", [])
        deductions = request.data.get("deductions", 0)
        bonus = request.data.get("bonus", 0)
        payment_method = request.data.get("payment_method")
        remarks = request.data.get("remarks", "")
        cheque_number = request.data.get("cheque_number")
        created_at = request.data.get("created_at")
        fund_account_id = request.data.get("fund_account_id")

        if not employees_ids or not months or not payment_method:
            return Response({"error": "employees, months, and payment_method are required"}, status=400)
        
        if payment_method == "Cheque" and not cheque_number:
            return Response({"error": "Cheque number is required for cheque payment."}, status=400)

        if payment_method == "Cash" and cheque_number:
            return Response({"error": "Cheque number should not be provided for cash payment."}, status=400)

        if payment_method == "Online" and not fund_account_id:
            return Response({"error": "Fund account ID is required for online payment."}, status=400)


        if payment_method == "Cheque" and cheque_number:
            if Payment.objects.filter(cheque_number=cheque_number).exists():
                return Response({"error": "This cheque number is already used."}, status=400)


        created_at_obj = datetime.strptime(created_at, "%Y-%m-%d")
        if created_at_obj.date() > date.today():
            return Response({"error": "created_at cannot be in the future."}, status=400)

        # Ensure employees is always defined
        employees = Employee.objects.filter(id__in=employees_ids)
        if not employees.exists():
            return Response({"error": "No employees found with the given IDs."}, status=400)

        today = date.today()
        current_year = SchoolYear.objects.get(start_date__lte=today, end_date__gte=today)

        created_salaries = []
        total_amount = 0
        messages = []

        for employee in employees:
            employee_email = employee.user.email  # Correct variable

            # Fetch teacher/staff for phone number
            teacher = Teacher.objects.filter(user__email=employee_email).first()
            staff = OfficeStaff.objects.filter(user__email=employee_email).first()
            phone_no = teacher.phone_no if teacher else (staff.phone_no if staff else None)

            # Bank account
            try:
                bank_account = BankingDetail.objects.get(user__email=employee_email, is_active=True)
                account_no = bank_account.account_no
                ifsc_code = bank_account.ifsc_code
                print("print statement : ",bank_account,account_no,ifsc_code)
            except BankingDetail.DoesNotExist:
                account_no = None
                ifsc_code = None

            for month in months:
                if EmployeeSalary.objects.filter(user=employee, month=month, school_year=current_year).exists():
                    messages.append(f"Salary already exists for {employee.user.get_full_name()} - {month}")
                    continue

                # gross = employee.base_salary
                # net_amount = gross + bonus - deductions
                # total_amount += net_amount

                gross = employee.base_salary
                net_amount = gross + bonus - deductions

                # Skip if net_amount is 0 or negative
                if net_amount <= 0:
                    messages.append(f"Cannot create salary for {employee.user.get_full_name()} {month}: deductions {deductions} exceed or equal base salary {gross}.")
                    continue

                total_amount += net_amount


                payment_status = "Success" if payment_method == "Cash" else "Pending"
                payment = Payment.objects.create(
                    amount=net_amount,
                    payment_method=payment_method,
                    status=payment_status,
                    payment_date=timezone.now(),
                    cheque_number=cheque_number if payment_method == "Cheque" else None
                )

                #  Add RazorpayX
                if payment_method == "Online":
                    auth = HTTPBasicAuth(settings.RAZORPAYX_KEY_ID, settings.RAZORPAYX_KEY_SECRET)

                    #create contact
                    response = requests.post(
                        "https://api.razorpay.com/v1/contacts",
                        auth=auth,
                        json={
                            "name": employee.user.get_full_name(),
                            "email": employee.user.email,
                            "contact": phone_no,
                            "type": "employee",
                            "reference_id": f"EMP-{employee.id}"
                        }
                    )
                    contact = response.json()
                    if "id" not in contact:
                        messages.append(f"Failed to create Razorpay contact for {employee.user.get_full_name()}: {contact.get('error', contact)}")
                        continue
                    contact_id = contact["id"]


                    #create fund account
                    response_fund = requests.post(
                        "https://api.razorpay.com/v1/fund_accounts",
                        auth=auth,
                        json={
                            "contact_id": contact_id,
                            "account_type": "bank_account",
                            "bank_account": {
                                "name": employee.user.get_full_name(),
                                "ifsc": ifsc_code,
                                "account_number": account_no
                            }
                        }
                    )
                    fund = response_fund.json()
                    if "id" not in fund:
                        messages.append(f"Failed to create fund account for {employee.user.get_full_name()}: {fund.get('error', fund)}")
                        continue
                    fund_id = fund["id"]

                    #safe narration for RazorpayX
                    import re
                    narration_text = f"Salary {month} {employee.user.get_full_name()}"
                    narration_text = re.sub(r"[^A-Za-z0-9\s]", "", narration_text)  # Only letters, numbers, space
                    narration_text = narration_text[:30]  

                    mode = "RTGS" if net_amount >= 200000 else "IMPS"

                    #initiate payout
                    response_payout = requests.post(
                        "https://api.razorpay.com/v1/payouts",
                        auth=auth,
                        json={
                            "account_number": settings.RAZORPAYX_ACCOUNT_NUMBER,
                            "fund_account_id": fund_id,
                            "amount": int(net_amount * 100),
                            "currency": "INR",
                            # "mode": "RTGS",
                            "mode": mode,
                            "queue_if_low_balance": True,
                            "purpose": "salary",
                            "narration": narration_text
                        }
                    )
                    payout = response_payout.json()
                    print(" RazorpayX Payout Response:", payout)

                    if getattr(settings, "TEST_MODE", False) and payment_method == "Online":
                        payment.status = "Success"  
                    else:
                        status_map = {
                            "processing": "Pending",
                            "queued": "Pending",
                            "pending": "Pending",
                            "processed": "Success",
                            "failed": "Failed",
                            "reversed": "Failed"
                        }
                        payment.status = status_map.get(payout.get("status", "").lower(), "Pending")

                    payment.contact_id = contact.get("id")
                    payment.fund_account_id = fund.get("id")
                    payment.payout_id = payout.get("id")
                    payment.save()

                salary = EmployeeSalary.objects.create(
                    user=employee,
                    school_year=current_year,
                    month=month,
                    gross_amount=gross,
                    bonus=bonus,
                    deductions=deductions,
                    net_amount=net_amount,
                    created_at=created_at,
                    payment=payment,
                    paid_by=request.user if payment_method.lower() == "cash" else None,
                    remarks=remarks
                )
                created_salaries.append(salary)

        return Response({
            "message": " | ".join(messages) if messages else "Salaries created successfully",
            "total_amount": total_amount,
            "salaries": EmployeeSalarySerializer(created_salaries, many=True).data
        })

    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        request_user = request.user
        roles = [role.name.lower() for role in request_user.role.all()]

        # EMPLOYEE SALARY fields allowed
        salary_allowed = ["remarks"]

        # PAYMENT fields allowed
        payment_allowed = ["payment_date", "status", "cheque_number"]

        # Block fields that should never update
        restricted_fields = [
            "employees", "months", "deductions", "bonus",
            "payment_method", "fund_account_id"
        ]
        for field in restricted_fields:
            if field in serializer.validated_data:
                return Response(
                    {"error": f"{field} cannot be updated once created."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # ----- UPDATE EMPLOYEE SALARY FIELDS -----
        for field in salary_allowed:
            if field in serializer.validated_data:
                setattr(instance, field, serializer.validated_data[field])

        # ----- UPDATE PAYMENT FIELDS -----
        payment = instance.payment
        if payment:

            # Payment Status (Director Only)
            if "status" in serializer.validated_data:
                if "director" not in roles:
                    return Response(
                        {"error": "Only Director can update salary status."},
                        status=status.HTTP_403_FORBIDDEN
                    )
                payment.status = serializer.validated_data["status"]
                instance.paid_by = request_user

            # Payment Date
            if "payment_date" in serializer.validated_data:
                payment.payment_date = serializer.validated_data["payment_date"]

            # Cheque Number
            if "cheque_number" in serializer.validated_data:
                payment.cheque_number = serializer.validated_data["cheque_number"]

            payment.save()

        instance.save()

        return Response({
            "message": "Salary updated successfully",
            "data": self.get_serializer(instance).data
        })

class IncomeCategoryView(viewsets.ModelViewSet):
    queryset = IncomeCategory.objects.all()
    serializer_class = IncomeCategorySerializer
    permission_classes = [IsAuthenticated,IsDirectororOfficeStaff]

class SchoolIncomeViewSet(viewsets.ModelViewSet):
    queryset = SchoolIncome.objects.all()
    serializer_class = SchoolIncomeSerializer
    permission_classes = [IsAuthenticated,IsDirectororOfficeStaff]
    
    def get_queryset(self):
        qs = super().get_queryset()
        request = self.request
        today = date.today()
        # the current school year
        current_school_year = SchoolYear.objects.filter(
            Q(start_date__lte=today), Q(end_date__gte=today)
        ).first()

        # skip filters on single-object actions
        if self.action in ["retrieve", "update", "partial_update", "destroy"]:
            return qs   

        # Get school_year param
        school_year_id = request.query_params.get("school_year")

        if school_year_id:
            qs = qs.filter(school_year_id=school_year_id) 
        elif current_school_year:
            qs = qs.filter(school_year=current_school_year)
            
        # apply optional filters
        category_id = request.query_params.get("category")
        if category_id:
            qs = qs.filter(category_id=category_id)

        month = request.query_params.get("month")
        if month:
            qs = qs.filter(month=month)

       
        return qs

class SchoolTurnOverViewSet(viewsets.ModelViewSet):
    queryset = SchoolTurnOver.objects.all()
    serializer_class = SchoolTurnOverSerializer
    permission_classes = [IsAuthenticated,IsDirectororOfficeStaff]  # keep your custom perms if needed

    def get_queryset(self):
        queryset = SchoolTurnOver.objects.all()

        school_year = self.request.query_params.get("school_year")
        verified_by = self.request.query_params.get("verified_by")
        is_locked = self.request.query_params.get("is_locked")

        if school_year:
            queryset = queryset.filter(school_year__id=school_year)
        if verified_by:
            queryset = queryset.filter(verified_by__id=verified_by)
        if is_locked is not None:
            queryset = queryset.filter(is_locked=is_locked.lower() == "true")

        return queryset

    def update(self, request, *args, **kwargs):
        if request.method == "PUT":
            return Response(
                {"detail": "PUT is not allowed. Use PATCH instead."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )
        return super().update(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        instance = serializer.save()

        # fetch previous year carry_forward
        prev_year = SchoolYear.objects.filter(id=instance.school_year.id - 1).first()
        if prev_year:
            try:
                prev_turnover = SchoolTurnOver.objects.get(school_year=prev_year)
                instance.carry_forward = {str(prev_year.year_name): float(prev_turnover.net_turnover or 0)}
                instance.save(update_fields=["carry_forward"])
            except SchoolTurnOver.DoesNotExist:
                pass
        
        self.update_totals(instance)

        # optional: auto-lock if needed
        if instance.is_locked:
            self._handle_verification(instance, self.request.user)

    def perform_update(self, serializer):
        instance_before = self.get_object()  # current DB state before save
        was_locked = instance_before.is_locked

        instance = serializer.save()
        self.update_totals(instance)

        # if it was unlocked and now locked -> verify + carry
        if instance.is_locked and not was_locked:
            self._handle_verification(instance, self.request.user)

    def perform_destroy(self, instance):
        if instance.is_locked:
            raise ValidationError("This turnover is locked and cannot be deleted.")
        super().perform_destroy(instance)

    # def update_totals(self, instance):
    #     income_sum = (
    #         SchoolIncome.objects.filter(
    #             school_year=instance.school_year, status="confirmed"
    #         ).aggregate(total=Sum("amount"))["total"]
    #         or 0
    #     )

    #     expense_sum = (
    #         SchoolExpense.objects.filter(
    #             school_year=instance.school_year, status="approved"
    #         ).aggregate(total=Sum("amount"))["total"]
    #         or 0
    #     )

    #     instance.total_income = income_sum
    #     instance.total_expense = expense_sum

    #     # calculate yearly profit
    #     yearly_profit = income_sum - expense_sum

    #     # add carry_forward safely as Decimal
    #     cf_total = sum(Decimal(str(v)) for v in instance.carry_forward.values()) if instance.carry_forward else Decimal(0)

    #     instance.net_turnover = yearly_profit + cf_total

    #     instance.save(update_fields=["total_income", "total_expense", "net_turnover"])
    def update_totals(self, instance):
        # calculate totals.
        income_sum = (
            SchoolIncome.objects.filter(
                school_year=instance.school_year, status="confirmed"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        expense_sum = (
            SchoolExpense.objects.filter(
                school_year=instance.school_year, status="approved"
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        instance.total_income = income_sum
        instance.total_expense = expense_sum

        # existing logic: yearly profit
        yearly_profit = income_sum - expense_sum

        # add carry_forward safely as Decimal
        cf_total = sum(Decimal(str(v)) for v in instance.carry_forward.values()) if instance.carry_forward else Decimal(0)

        # net turnover = yearly profit + carry_forward
        instance.net_turnover = yearly_profit + cf_total

        # ---- new logic: financial outcome & status ----
        instance.financial_outcome = yearly_profit  # same as income - expense
        if instance.financial_outcome > 0:
            instance.financial_status = "Profit"
        elif instance.financial_outcome < 0:
            instance.financial_status = "Loss"
        else:
            instance.financial_status = "Break-even"
        # ------------------------------------------------

        # save all fields together
        instance.save(update_fields=[
            "total_income", "total_expense", "net_turnover",
            "financial_outcome", "financial_status"
        ])
   
    def _handle_verification(self, instance, user):
        if not instance.is_locked:
            instance.is_locked = True

        if user and getattr(user, "is_authenticated", False):
            instance.verified_by = user

        if not instance.verified_at:
            instance.verified_at = timezone.now()

        instance.save(update_fields=["verified_by", "verified_at", "is_locked"])



class MasterFeeViewSet(viewsets.ModelViewSet):
    queryset = MasterFee.objects.all()
    serializer_class = MasterFeeSerializer
    permission_classes = [IsAuthenticated]


class FeeStructureViewSet(viewsets.ModelViewSet):
    queryset = FeeStructure.objects.all()
    serializer_class = FeeStructureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        year_level_id = self.request.query_params.get("year_level_id")
        if year_level_id:
            queryset = queryset.filter(year_level__id=year_level_id)
        return queryset



class FeePaymentView(viewsets.ModelViewSet):
    queryset = FeePayment.objects.all()
    serializer_class = FeePaymentSerializer
    permission_classes = [IsAuthenticated]

import uuid
class StudentFeeView(viewsets.ModelViewSet):
    queryset = StudentFee.objects.all()
    serializer_class = StudentFeeSerializer
    permission_classes = [IsAuthenticated]


    # def generate_receipt_number(self):
    #     # return f"RCPT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    #     # return f"R{timezone.now().strftime('%y%m%d%H%M')}"[:10]
    #     now = timezone.now().strftime('%y%m%d%H%M%S')
    #     rand = random.randint(100, 999)
    #     return f"R{now}{rand}"
    
    # def generate_receipt_number(self):
    #     return f"R{uuid.uuid4().hex[:12].upper()}"

    # def generate_receipt_number(self):
    #     while True:
    #         now = timezone.now().strftime('%y%m%d%H%M%S')
    #         rand = random.randint(100, 999)
    #         receipt = f"R{now}{rand}"
    #         if not StudentFee.objects.filter(receipt_number=receipt).exists():
    #             return receipt

    def generate_receipt_number(self):
        today = timezone.now().strftime('%Y%m%d')
        last_receipt = StudentFee.objects.filter(receipt_number__startswith=f'REC-{today}').aggregate(Max('receipt_number'))

        if last_receipt['receipt_number__max']:
            parts = last_receipt['receipt_number__max'].split('-')
            last_number = int(parts[-2])
            new_number = last_number + 1
        else:
            new_number = 1

        unique_suffix = uuid.uuid4().hex[:4].upper()
        return f'REC-{today}-{new_number:05d}-{unique_suffix}'

    
    @action(detail=False, methods=["get"], url_path="student_unpaid_fees")
    def student_unpaid_fees(self, request):
        queryset = StudentFee.objects.filter(status__in=["pending", "partial"]).select_related(
            "student_year__student", "student_year__level", "school_year", "fee_structure"
        ).prefetch_related("payments")

        grouped = {}
        for fee in queryset:
            student = fee.student_year.student
            student_id = student.id
            month_name = calendar.month_name[fee.month] if fee.month else "Unknown"
            school_year_name = fee.school_year.year_name if fee.school_year else "Unknown"
            year_level = fee.student_year.level.level_name

            if student_id not in grouped:
                grouped[student_id] = {
                    "student": {
                        "id": student_id,
                        "name": f"{student.user.first_name} {student.user.last_name}",
                        "scholar_number": student.scholar_number 
                    },
                    "month": month_name,
                    "school_year": school_year_name,
                    "year_level_fees_grouped": [],
                    "total_amount": Decimal("0.00"),
                    "paid_amount": Decimal("0.00"),
                    "due_amount": Decimal("0.00"),
                }

            yl_group = next((yl for yl in grouped[student_id]["year_level_fees_grouped"] if yl["year_level"] == year_level), None)
            if not yl_group:
                yl_group = {"year_level": year_level, "fees": []}
                grouped[student_id]["year_level_fees_grouped"].append(yl_group)

            yl_group["fees"].append({
                "id": fee.id,
                "fee_type": fee.fee_structure.fee_type,
                "amount": str(fee.original_amount)
            })

            grouped[student_id]["total_amount"] += fee.original_amount
            grouped[student_id]["paid_amount"] += fee.paid_amount
            grouped[student_id]["due_amount"] += fee.due_amount

        for student_data in grouped.values():
            student_data["total_amount"] = str(student_data["total_amount"])
            student_data["paid_amount"] = str(student_data["paid_amount"])
            student_data["due_amount"] = str(student_data["due_amount"])

        return Response({"unpaid_fees": list(grouped.values())})
  


    @action(detail=False, methods=["get"], url_path="overdue_fees")
    def overdue_fees(self, request):
        student_year_id = request.query_params.get("student_year_id")
        month = request.query_params.get("month")  # month as integer (1-12)
        school_year_id = request.query_params.get("school_year_id")
        today = timezone.now().date()

        queryset = StudentFee.objects.filter(due_amount__gt=0, due_date__lt=today)

        if student_year_id:
            queryset = queryset.filter(student_year_id=student_year_id)
        
        if school_year_id:
            queryset = queryset.filter(school_year_id=school_year_id)
        
        if month:
            queryset = queryset.filter(due_date__month=int(month))

        if student_year_id:
            queryset = queryset.filter(student_year_id=student_year_id)
        
        if school_year_id:
            queryset = queryset.filter(school_year_id=school_year_id)

        response_data = []
        for fee in queryset:
            response_data.append({
                "fee_id": fee.id,
                "fee_type": getattr(fee.fee_structure, 'fee_type', 'N/A'),
                "original_amount": str(fee.original_amount),
                "paid_amount": str(fee.paid_amount),
                "due_amount": str(fee.due_amount),
                "status": "Overdue",
                "due_date": fee.due_date.strftime("%Y-%m-%d")
            })

        return Response(response_data, status=drf_status.HTTP_200_OK)


    @action(detail=False, methods=["get"], url_path="overdue_fees")
    def overdue_fees(self, request):
        student_year_id = request.query_params.get("student_year_id")
        month = request.query_params.get("month")  # optional filter
        school_year_id = request.query_params.get("school_year_id")
        today = timezone.now().date()

        queryset = StudentFee.objects.filter(due_amount__gt=0, due_date__lt=today)

        if student_year_id:
            queryset = queryset.filter(student_year_id=student_year_id)
        if school_year_id:
            queryset = queryset.filter(school_year_id=school_year_id)
        if month:
            queryset = queryset.filter(due_date__month=int(month))

        response_data = []
        for fee in queryset:
            student_year = fee.student_year
            student = getattr(student_year, 'student', None)
            year_level = getattr(student_year, 'level', None)

            if student and student.user:
                student_name = f"{student.user.first_name} {student.user.last_name}"
            else:
                student_name = "N/A"

            response_data.append({
                "fee_id": fee.id,
                "fee_type": getattr(fee.fee_structure, 'fee_type', 'N/A'),
                "original_amount": str(fee.original_amount),
                "paid_amount": str(fee.paid_amount),
                "due_amount": str(fee.due_amount),
                "status": "Overdue",
                "due_date": fee.due_date.strftime("%Y-%m-%d"),
                "student_name": student_name,
                "scholar_number": getattr(student, 'scholar_number', 'N/A'),
                "class_name": getattr(year_level, 'level_name', 'N/A'),  # <- change name to level_name
                "month": calendar.month_name[fee.due_date.month]  # <- Month ka name
            })

        return Response(response_data, status=drf_status.HTTP_200_OK)


    @action(detail=False, methods=['post'], url_path='submit_fee')
    def submit_fee(self, request):
        payment_mode = request.data.get("payment_method", "").lower()
        cheque_number = request.data.get("cheque_number") 
        student_year_id = request.data.get("student_year_id")
        school_year_id = request.data.get("school_year_id")
        fees_data = request.data.get("fees", [])

        if not student_year_id or not fees_data:
            return Response(
                {"error": "student_year_id and fees are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_amount = Decimal("0.00")
        created_records = []

        try:
            student_year = StudentYearLevel.objects.get(id=student_year_id)
        except StudentYearLevel.DoesNotExist:
            return Response({"error": "StudentYearLevel not found."}, status=status.HTTP_400_BAD_REQUEST)

        discounts = AppliedFeeDiscount.objects.filter(student=student_year)

        for fee_data in fees_data:
            # amount_paid = Decimal(str(fee_data.get("amount", "0.00")))
            amount_paid = Decimal(str(fee_data.get("amount", "0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            serializer = self.get_serializer(
                data={
                    "student_year_id": student_year_id,
                    "fee_structure_id": fee_data.get("fee_type_id"),
                    "school_year_id": school_year_id,
                    "month": fee_data.get("month"),
                },
                context={'request': request, 'payment_method': payment_mode}
            )
            serializer.is_valid(raise_exception=True)
            student_fee = serializer.save()

            due_date_str = fee_data.get("due_date")
            if due_date_str:
                student_fee.due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d").date()
            else:
                month = int(fee_data.get("month"))
                year = timezone.now().year
                student_fee.due_date = date(year, month, 15)

            discount_obj = AppliedFeeDiscount.objects.filter(
                student=student_year,
                fee_type=student_fee.fee_structure
            ).first()

            discount_amount = Decimal(str(discount_obj.discount_amount if discount_obj else 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            student_fee.applied_discount = bool(discount_obj)

            max_payable = (student_fee.original_amount - discount_amount - student_fee.paid_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if max_payable < 0:
                max_payable = Decimal("0.00")

            if amount_paid > max_payable:
                return Response(
                    {"error": f"Amount cannot exceed due amount after discount: {max_payable}"},
                    status=status.HTTP_400_BAD_REQUEST
                )


            FeePayment.objects.create(
                student_fee=student_fee,
                amount=amount_paid,
                payment_method=payment_mode,
                cheque_number=cheque_number,
                status="success" if payment_mode != "online" else "initiated",
                payment_date=timezone.now() if payment_mode != "online" else None,
                received_by=request.user,
                notes=f"Fee payment for {student_fee.fee_structure.fee_type} - Month {student_fee.month}"
            )

            student_fee.paid_amount = FeePayment.objects.filter(student_fee=student_fee).aggregate(
                total=Sum('amount')
            )['total'] or Decimal("0.00")


            today = timezone.now().date()
            if (student_fee.fee_structure.fee_type.lower() == "tuition fee"
                    and student_fee.due_date
                    and today > student_fee.due_date):
                student_fee.penalty_amount = Decimal("25.00")
            else:
                student_fee.penalty_amount = Decimal("0.00")

            # student_fee.due_amount = max(student_fee.original_amount - student_fee.paid_amount - discount_amount + student_fee.penalty_amount, Decimal("0.00"))

            student_fee.due_amount = max(
                student_fee.original_amount - student_fee.paid_amount - discount_amount + student_fee.penalty_amount,
                Decimal("0.00")
            )

            if payment_mode == "online":
                student_fee.status = "pending"
            else:
                student_fee.due_amount = student_fee.original_amount - student_fee.paid_amount + student_fee.penalty_amount
                if student_fee.due_amount <= 0:
                    student_fee.status = "paid"
                elif student_fee.paid_amount > 0:
                    student_fee.status = "partial"
                else:
                    student_fee.status = "pending"

            student_fee.save()

            total_amount += amount_paid
            created_records.append(student_fee)

        if payment_mode == "online":
            return self.initiate_payment(request)

        output_serializer = self.get_serializer(created_records, many=True)
        return Response({
            "message": f"{len(created_records)} fee records submitted successfully!",
            "total_amount_paid": total_amount,
            "payment_mode": payment_mode,
            "data": output_serializer.data
        }, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=["get"], url_path="fee_history")
    def fee_history(self, request):
            student_year_id = request.query_params.get("student_year_id")
            school_year_id = request.query_params.get("school_year_id")
            
            if not student_year_id or not school_year_id:
                return Response({"detail": "student_year_id and school_year_id are required"},
                                status=status.HTTP_400_BAD_REQUEST)
            
            student_fees = StudentFee.objects.filter(
                student_year_id=student_year_id,
                school_year_id=school_year_id
            ).prefetch_related('payments', 'fee_structure')

            result = []
            for sf in student_fees:
                payments = sf.payments.all()
                result.append({
                    "fee_type": sf.fee_structure.fee_type,
                    "original_amount": str(sf.original_amount),
                    "paid_amount": str(sf.paid_amount),
                    "due_amount": str(sf.due_amount),
                    "status": sf.status,
                    "month": calendar.month_name[sf.month] if sf.month else None,
                    "payments": [{
                        "amount": str(p.amount),
                        "method": p.payment_method,
                        "status": p.status,
                        "date": p.payment_date
                    } for p in payments]
                })
            return Response(result)


    @action(detail=False, methods=["get"], url_path="pending_fees")
    def pending_fees(self, request):
        school_year_id = request.query_params.get("school_year_id")
        if not school_year_id:
            return Response({"detail": "school_year_id is required"},
                            status=status.HTTP_400_BAD_REQUEST)

        pending_fees = StudentFee.objects.filter(
            school_year_id=school_year_id
        ).exclude(status="paid")

        if not pending_fees.exists():
            return Response({"detail": "No pending fees found."}, status=status.HTTP_404_NOT_FOUND)

        response_data = []
        for fee in pending_fees:
            discount_obj = AppliedFeeDiscount.objects.filter(student=fee.student_year, fee_type=fee.fee_structure).first()
            discount_amount = discount_obj.discount_amount if discount_obj else 0

            adjusted_original_amount = max(fee.original_amount - discount_amount, 0)

            response_data.append({
                "fee_id": fee.id,
                "fee_type": fee.fee_structure.fee_type,
                "original_amount": str(adjusted_original_amount),
                "paid_amount": str(fee.paid_amount),
                "status": fee.status
            })

        return Response(response_data)


    @action(detail=False, methods=["get"], url_path="fee_preview")
    def preview(self, request):
        student_year_id = request.query_params.get("student_year_id")

        if not student_year_id:
            return Response({"detail": "student_year_id is required"}, status=drf_status.HTTP_400_BAD_REQUEST)

        try:
            student_year_level = StudentYearLevel.objects.get(id=student_year_id)
        except StudentYearLevel.DoesNotExist:
            return Response({"detail": "StudentYearLevel not found"}, status=drf_status.HTTP_404_NOT_FOUND)

        year_level = student_year_level.level
        year_level_fees = FeeStructure.objects.filter(year_level=year_level)
        paid_fees = StudentFee.objects.filter(student_year=student_year_level)

        MONTHS = {month: i for i, month in enumerate(calendar.month_name) if month}

        result = []

        for month_name, month_number in MONTHS.items():
            month_data = {"month": month_name, "fees": []}

            for fee in year_level_fees:
                discount_total = AppliedFeeDiscount.objects.filter(
                    student=student_year_level,
                    fee_type=fee
                ).aggregate(total_discount=Sum('discount_amount'))['total_discount'] or Decimal('0.00')

                base_amount = Decimal(fee.fee_amount) - Decimal(discount_total)
                # print(base_amount)
                base_amount = max(base_amount, Decimal('0.00'))  
                if fee.fee_type.lower() == "admission fee":
                    if month_name != "January":
                        continue
                    total_paid = paid_fees.filter(fee_structure=fee).aggregate(
                        Sum('paid_amount')
                    )['paid_amount__sum'] or Decimal('0.00')
                else:
                    total_paid = paid_fees.filter(
                        fee_structure=fee,
                        month=month_number
                    ).aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')

                if total_paid >= base_amount and base_amount > 0:
                    status_str = "Paid"
                elif total_paid > 0:
                    status_str = "Partially Paid"
                else:
                    status_str = "Pending"

                month_data["fees"].append({
                    "fee_id": fee.id,
                    "fee_type": fee.fee_type,
                    "original_amount": str(base_amount),
                    "paid_amount": str(total_paid),
                    "status": status_str,
                    "applied_discount": str(discount_total)
                })

            if month_data["fees"]:
                result.append(month_data)

        return Response(result)


    @action(detail=False, methods=["POST"], url_path="initiate_payment")
    def initiate_payment(self, request):
        data = request.data.copy()
        student_year_id = data.get("student_year_id")
        fees_data = data.get("fees") or data.get("selected_fees") or []

        if not student_year_id:
            return Response({"error": "Student_year_id missing - ye field required hai."}, status=400)

        if not fees_data:
            return Response({"error": "No fees selected - fees data empty hai."}, status=400)

        try:
            student_year = StudentYearLevel.objects.get(id=student_year_id)
        except StudentYearLevel.DoesNotExist:
            return Response({"error": "Invalid student_year_id."}, status=400)

        receipt_number = self.generate_receipt_number()
        created_fees = []

        for fee_dict in fees_data:
            fee_id = fee_dict.get("fee_id") or fee_dict.get("fee_type_id")
            month = fee_dict.get("month")
            try:
                fee_obj = FeeStructure.objects.get(id=fee_id)
            except FeeStructure.DoesNotExist:
                continue

            school_year_id = data.get("school_year_id")
            if school_year_id:
                try:
                    school_year = SchoolYear.objects.get(id=school_year_id)
                except SchoolYear.DoesNotExist:
                    return Response({"error": "Invalid school_year_id"}, status=400)
            else:
                school_year = get_current_school_year()  # fallback


            student_fee, created = StudentFee.objects.get_or_create(
                student_year=student_year,
                fee_structure=fee_obj,
                school_year=school_year,
                month=month,
                defaults={
                    "original_amount": fee_obj.fee_amount,
                    "paid_amount": Decimal("0.00"),
                    "due_amount": fee_obj.fee_amount,
                    "status": "pending",
                    "receipt_number": receipt_number
                }
            )

            created_fees.append(student_fee)

        total_amount = sum(Decimal(str(fee_dict.get("amount") or fee_dict.get("paid_amount", 0))) for fee_dict in fees_data)

        if total_amount < Decimal("1.00"):
            return Response({"error": "Paid amount must be at least 1 INR to create Razorpay order."}, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            razorpay_order = client.order.create({
                "amount": int(total_amount * 100),
                "currency": "INR",
                "payment_capture": "1",
                "receipt": receipt_number
            })
        except Exception as e:
            return Response({"error": f"Razorpay order creation failed: {str(e)}"}, status=500)

        return Response({
            "message": "Payment initiated successfully - status pending.",
            "razorpay_order_id": razorpay_order["id"],
            "receipt_number": receipt_number,
            "fees": [
                {
                    "id": f.id,
                    "fee_type": f.fee_structure.fee_type,
                    "status": f.status,
                    "due_amount": str(f.due_amount),
                    "month": f.month
                } for f in created_fees
            ]
        }, status=200)


    @action(detail=False, methods=["post"], url_path="confirm_payment")
    def confirm_payment(self, request):
        data = request.data.copy()
        required_fields = [
            "student_year_id", "selected_fees",
            "payment_mode", "received_by", 
            "razorpay_order_id", "razorpay_payment_id", "razorpay_signature"
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return Response({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        student_year_id = data["student_year_id"]
        selected_fees = data["selected_fees"]  
        payment_mode = data["payment_mode"]
        received_by = data["received_by"]

        try:
            student_year = StudentYearLevel.objects.get(id=student_year_id)
        except StudentYearLevel.DoesNotExist:
            return Response({"error": "Invalid student_year_id."}, status=400)

        created_payments = []

        for fee_item in selected_fees:
            fee_id = fee_item.get("fee_id") or fee_item.get("fee_type_id")

            month = fee_item.get("month")
            paid_amount = Decimal(str(fee_item.get("paid_amount") or fee_item.get("amount", 0)))

            if paid_amount < 0:
                return Response({"error": f"Paid amount missing or zero for fee_id {fee_id}."}, status=400)

            try:
                fee_obj = FeeStructure.objects.get(id=fee_id)
            except FeeStructure.DoesNotExist:
                return Response({"error": f"FeeStructure not found for fee_id {fee_id}."}, status=400)

            student_fee_qs = StudentFee.objects.filter(
                student_year=student_year,
                fee_structure=fee_obj
            )
            if month:
                student_fee_qs = student_fee_qs.filter(month=month)

            student_fee = student_fee_qs.first()
            if not student_fee:
                return Response(
                    {"error": f"StudentFee record not found for fee_id {fee_id} and month {month}. Please initiate payment first."},
                    status=400
                )

            if paid_amount > student_fee.original_amount:
                return Response(
                    {"error": f"Paid amount cannot exceed original amount ({student_fee.original_amount}) for fee_id {fee_id}."},
                    status=400
                )

            student_fee.paid_amount += paid_amount
            student_fee.due_amount = max(student_fee.original_amount - student_fee.paid_amount, Decimal("0.00"))
            student_fee.status = "paid" if student_fee.due_amount == 0 else "partial"
            student_fee.save()

            payment = FeePayment.objects.create(
                student_fee=student_fee,
                amount=paid_amount,
                payment_method=payment_mode,
                status="success",
                payment_date=timezone.now(),
                received_by_id=received_by,
                razorpay_order_id=data["razorpay_order_id"],
                razorpay_payment_id=data["razorpay_payment_id"],
                razorpay_signature=data["razorpay_signature"]
            )
            created_payments.append(payment)

        return Response({
            "message": "Payment confirmed successfully.",
            "payments": [
                {
                    "id": p.id,
                    "fee_type": p.student_fee.fee_structure.fee_type,
                    "amount": str(p.amount),
                    "status": p.status,
                    "month": p.student_fee.month,
                    "receipt_number": p.student_fee.receipt_number
                } for p in created_payments
            ]
        }, status=201)


def student_display_name(student):
    return f"{student.user.first_name} {student.user.last_name}"
class AppliedFeeDiscountViewSet(viewsets.ModelViewSet):
    queryset = AppliedFeeDiscount.objects.all()
    serializer_class = AppliedFeeDiscountSerializer 
    permission_classes = [IsAuthenticated]


    def list(self, request):
        student_year_id = request.query_params.get("student_year_id")

        if student_year_id:
            return Response({
                "available_fees": self.get_available_fees(student_year_id),
                "applied_discounts": self.get_applied_discounts(student_year_id)
            })
        else:
            queryset = self.queryset.select_related(
                "student", "student__level", "student__year", "fee_type", "approved_by"
            )
            serializer = AppliedFeeDiscountSerializer(queryset, many=True)
            return Response(serializer.data)

    def get_available_fees(self, student_year_id):
        fees = StudentFee.objects.filter(
            student_year_id=student_year_id,
            status__in=["pending", "partial"]
        ).select_related(
            'student_year',
            'student_year__student',
            'student_year__level',
            'student_year__year',
            'fee_structure'
        )

        fee_list = []
        for fee in fees:
            original_amount = Decimal(str(fee.original_amount))
            due_amount = Decimal(str(fee.due_amount))
            fee_list.append({
                "student_fee_id": fee.id,
                "student_year_id": fee.student_year.id,
                "student_class": fee.student_year.level.level_name if fee.student_year.level else None,
                "school_year": fee.student_year.year.year_name if fee.student_year.year else None,
                "fee_type": fee.fee_structure.fee_type,
                "original_amount": float(original_amount),
                "due_amount": float(due_amount),
                "student_name": student_display_name(fee.student_year.student)
            })
        return fee_list

    def get_applied_discounts(self, student_year_id):
        discounts = AppliedFeeDiscount.objects.filter(
            student_id=student_year_id
        ).select_related(
            "student", "student__level", "student__year", "fee_type", "approved_by"
        )

        discount_list = []
        for d in discounts:
            original_amount = Decimal(str(d.fee_type.fee_amount))
            discount_amount = d.discount_amount
            discount_percentage = (discount_amount / original_amount * Decimal('100')) if original_amount else Decimal('0')

            discount_list.append({
                "id": d.id,
                "student": student_display_name(d.student.student),
                "student_year_id": d.student.id,
                "student_class": d.student.level.level_name if d.student.level else None,
                "school_year": d.student.year.year_name if d.student.year else None,
                "fee_type": d.fee_type.fee_type,
                "discount_name": d.discount_name,
                "discount_amount": float(discount_amount),
                "discounted_amount_percent": float(discount_percentage),
                "approved_by": getattr(d.approved_by, "username", "Admin"),
                "approved_at": d.approved_at,
            })

        return discount_list


    @action(detail=False, methods=["post"], url_path="apply")
    @transaction.atomic

    def apply_discount(self, request):
        user = request.user
        student_year_id = request.data.get("student_year_id")
        fee_structure_id = request.data.get("fee_structure_id")
        discount_name = request.data.get("discount_name")
        discount_percentage = request.data.get("discounted_amount_percent")

        user_roles = [r.name.lower() for r in request.user.role.all()]
        if "director" not in user_roles:
            return Response({"detail": "Only directors are authorized to apply discounts."}, status=403)

        if not all([student_year_id, fee_structure_id, discount_name, discount_percentage]):
            return Response(
                {"detail": "student_year_id, fee_structure_id, discount_name, and discounted_amount_percent are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            student_year = StudentYearLevel.objects.get(id=student_year_id)
            fee_structure = FeeStructure.objects.get(id=fee_structure_id)
        except (StudentYearLevel.DoesNotExist, FeeStructure.DoesNotExist):
            return Response(
                {"detail": "Invalid student_year_id or fee_structure_id."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not hasattr(student_year, "student") or not hasattr(student_year.student, "user"):
            return Response(
                {"detail": "Invalid student record. Discount can only be applied to valid students."},
                status=status.HTTP_400_BAD_REQUEST,
            )


        if not fee_structure.year_level.filter(id=student_year.level.id).exists():
            return Response({
                "detail": "Discount can only be applied to fees of the student's own class."
            }, status=400)

        try:
            discount_percent = Decimal(str(discount_percentage))
            if discount_percent < 0 or discount_percent > 100:
                return Response(
                    {"detail": "Discount percentage must be between 0 and 100."},
                    status=status.HTTP_400_BAD_REQUEST,
                )


            max_allowed_percent = Decimal("90.00")
            if discount_percent > max_allowed_percent:
                return Response(
                    {"detail": f"Discount cannot exceed {max_allowed_percent}% of the fee."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            fee_amount = Decimal(fee_structure.fee_amount or 0)
            final_discount_amount = (fee_amount * discount_percent) / Decimal("100")

            if final_discount_amount > fee_amount:
                return Response(
                    {"detail": "Discount amount cannot be greater than the fee amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except Exception as e:
            return Response(
                {"detail": f"Invalid discount percentage: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if AppliedFeeDiscount.objects.filter(student=student_year, fee_type=fee_structure).exists():
            return Response(
                {"detail": "Discount already applied for this student and fee type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        discount = AppliedFeeDiscount.objects.create(
            student=student_year,
            fee_type=fee_structure,
            discount_name=discount_name,
            discount_amount=final_discount_amount,
            approved_by=user,
            approved_at=timezone.now(),
        )

        return Response(
            {
                "detail": "Discount applied successfully",
                "student_name": f"{student_year.student.user.first_name} {student_year.student.user.last_name}",
                "student_year_id": student_year.id,
                "fee_type": fee_structure.fee_type,
                "discount_name": discount.discount_name,
                "discount_amount": float(final_discount_amount),
                "discounted_amount_percent": float(discount_percentage),
                "approved_by": getattr(user, "username", "Admin"),
            },
            status=status.HTTP_200_OK,
        )


    @action(detail=True, methods=["put"], url_path="update_discount")
    @transaction.atomic
    def update_discount(self, request, pk=None):
        user = request.user
        discount = self.get_object()  

        user_roles = [r.name.lower() for r in user.role.all()]
        if "director" not in user_roles:
            return Response({"detail": "Only directors can update discounts."}, status=403)

        discount_name = request.data.get("discount_name")
        discounted_amount_percent = request.data.get("discounted_amount_percent")

        if not all([discount_name, discounted_amount_percent]):
            return Response({"detail": "Both discount_name and discounted_amount_percent are required."}, status=400)

        try:
            discount_percent = Decimal(str(discounted_amount_percent))
            if not (0 <= discount_percent <= 100):
                raise ValueError("Discount must be 0-100%.")

            max_percent = Decimal("80.00")
            if discount_percent > max_percent:
                return Response({"detail": f"Discount cannot exceed {max_percent}%."}, status=400)

            fee_amount = Decimal(discount.fee_type.fee_amount or 0)
            final_discount_amount = (fee_amount * discount_percent) / Decimal("100")
        except Exception as e:
            return Response({"detail": f"Invalid discount percentage: {e}"}, status=400)

        discount.discount_name = discount_name
        discount.discount_amount = final_discount_amount
        discount.approved_by = user
        discount.approved_at = timezone.now()
        discount.save(update_fields=["discount_name", "discount_amount", "approved_by", "approved_at"])

        return Response({
            "detail": "Discount updated successfully",
            "student_name": student_display_name(discount.student.student),
            "student_year_id": discount.student.id,
            "fee_type": discount.fee_type.fee_type,
            "discount_name": discount.discount_name,
            "discount_amount": float(final_discount_amount),
            "discounted_amount_percent": float(discount_percent),
            "approved_by": getattr(user, "username", "Admin"),
        }, status=200)



# class DefaulterNotifyView(APIView):
#     def get(self, request):
#         year_level_id = request.query_params.get("year_level")
#         section = request.query_params.get("section")

#         # Filter class + section
#         admissions = Admission.objects.filter(is_active=True)

#         if year_level_id:
#             admissions = admissions.filter(year_level_id=year_level_id)

#         if section:
#             admissions = admissions.filter(class_section=section)

#         # Fetch students belonging to filtered admissions
#         student_year_ids = admissions.values_list("student__id", flat=True)
#         student_year_levels = StudentYearLevel.objects.filter(student_id__in=student_year_ids)

#         today = timezone.now().date()
#         three_months_before = today.replace(
#             year=today.year if today.month > 3 else today.year - 1,
#             month=(today.month - 3) if today.month > 3 else (12 - (3 - today.month)),
#         )

#         defaulters = []

#         for sy in student_year_levels:
#             fees = StudentFee.objects.filter(student_year=sy)

#             # Unpaid for last 3 months
#             unpaid_last_3 = fees.filter(
#                 month__gte=three_months_before.month,
#                 month__lte=today.month,
#                 status__in=["pending", "partial"]
#             ).exists()

#             # Any remaining dues
#             has_due = fees.filter(due_amount__gt=0).exists()

#             if unpaid_last_3 or has_due:
#                 defaulters.append(sy)

#         # Send email one-by-one (load-friendly)
#         for d in defaulters:
#             user = d.student.user
#             email = user.email

#             if email:
#                 # Fetch unpaid dues for that student
#                 unpaid_fees = StudentFee.objects.filter(
#                     student_year=d,
#                     status__in=["pending", "partial"],
#                     due_amount__gt=0
#                 )

#                 # Build fee details lines
#                 fee_lines = ""
#                 for fee in unpaid_fees:
#                     fee_lines += f"- {fee.fee_structure.fee_type}: ₹{fee.due_amount}\n"

#                 # Final email message
#                 subject = "Fee Due Notice"

#                 message = (
#                     f"Dear {user.first_name},\n\n"
#                     f"You have pending school fees. Here are the details:\n\n"
#                     f"{fee_lines}\n"
#                     f"Please clear your dues as soon as possible.\n\n"
#                     f"Thank you."
#                 )

#                 send_email_notification(email, subject, message)

#         return Response(
#             {
#                 "message": "Email notification sent to all defaulters.",
#                 "defaulters_count": len(defaulters),
#             },
#             status=status.HTTP_200_OK,
#         )

class DefaulterNotifyView(APIView):
    def get(self, request):
        year_level_id = request.query_params.get("year_level")
        section = request.query_params.get("section")

        # Filter class + section
        admissions = Admission.objects.filter(is_active=True)

        if year_level_id:
            admissions = admissions.filter(year_level_id=year_level_id)

        if section:
            admissions = admissions.filter(class_section=section)

        # Fetch students belonging to filtered admissions
        student_year_ids = admissions.values_list("student__id", flat=True)
        student_year_levels = StudentYearLevel.objects.filter(student_id__in=student_year_ids)

        today = timezone.now().date()
        three_months_before = today.replace(
            year=today.year if today.month > 3 else today.year - 1,
            month=(today.month - 3) if today.month > 3 else (12 - (3 - today.month)),
        )

        defaulters = []

        for sy in student_year_levels:
            fees = StudentFee.objects.filter(student_year=sy)

            # Unpaid for last 3 months
            unpaid_last_3 = fees.filter(
                month__gte=three_months_before.month,
                month__lte=today.month,
                status__in=["pending", "partial"]
            ).exists()

            # Any remaining dues
            has_due = fees.filter(due_amount__gt=0).exists()

            if unpaid_last_3 or has_due:
                defaulters.append(sy)

        # Send email one-by-one (load-friendly)
        for d in defaulters:
            user = d.student.user
            email = user.email
            phone = d.student.contact_number if hasattr(d.student, 'contact_number') else None

            # Build unpaid fee details
            unpaid_fees = StudentFee.objects.filter(
                student_year=d,
                status__in=["pending", "partial"],
                due_amount__gt=0
            )

            fee_lines = ""
            for fee in unpaid_fees:
                fee_lines += f"- {fee.fee_structure.fee_type}: ₹{fee.due_amount}\n"

            # Final message
            message = (
                f"Dear {user.first_name},\n\n"
                f"You have pending school fees:\n\n"
                f"{fee_lines}\n"
                f"Please clear your dues as soon as possible.\n\n"
                f"Thank you."
            )

            # Send Email
            if email:
                send_email_notification(email, "Fee Due Notice", message)

            # Send WhatsApp
            if phone:
                send_whatsapp(message, phone)
                result=send_whatsapp(message, phone)
                print("WHATSAPP RESULT =>", result)


        return Response(
            {
                "message": "Email notification and whatsapp message sent to all defaulters.",
                "defaulters_count": len(defaulters),
            },
            status=status.HTTP_200_OK,
        )
