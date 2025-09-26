from django.forms import DateField, ValidationError
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





client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

### Function to generate auto receipt no. called it inside initiate payment
def generate_receipt_number():
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not FeeRecord.objects.filter(receipt_number=code).exists():
                return code
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







@api_view(["GET"])
def director_fee_summary(request):
    month = request.GET.get("month")  
    year = request.GET.get("year")    

    # School-level summary
    total_students = Student.objects.count()

    fee_qs = FeeRecord.objects.all()

    if month and year:
        fee_qs = fee_qs.filter(month=month, payment_date__year=year)
    elif year:
        fee_qs = fee_qs.filter(payment_date__year=year)

    total_fee = fee_qs.aggregate(
        total=Coalesce(Sum('total_amount', output_field=DecimalField()), Decimal("0.00"))
    )['total']

    total_paid = fee_qs.aggregate(
        paid=Coalesce(Sum('paid_amount', output_field=DecimalField()), Decimal("0.00"))
    )['paid']

    total_due = fee_qs.aggregate(
        due=Coalesce(Sum('due_amount', output_field=DecimalField()), Decimal("0.00"))
    )['due']

    # Class-wise summary
    class_data = []
    all_class_periods = ClassPeriod.objects.select_related('classroom__room_type').all()

    for period in all_class_periods:
        students_in_class = Student.objects.filter(classes=period).distinct()
        student_ids = students_in_class.values_list('id', flat=True)

        class_fee_qs = FeeRecord.objects.filter(student_id__in=student_ids)
        if month and year:
            class_fee_qs = class_fee_qs.filter(month=month, payment_date__year=year)

        class_total_fee = class_fee_qs.aggregate(
            total=Coalesce(Sum('total_amount', output_field=DecimalField()), Decimal("0.00"))
        )['total']

        class_total_paid = class_fee_qs.aggregate(
            paid=Coalesce(Sum('paid_amount', output_field=DecimalField()), Decimal("0.00"))
        )['paid']

        class_total_due = class_fee_qs.aggregate(
            due=Coalesce(Sum('due_amount', output_field=DecimalField()), Decimal("0.00"))
        )['due']

        class_data.append({
            "class_name": f"{period.classroom.room_type} - {period.classroom.room_name}",
            "total_students": students_in_class.count(),
            "total_fee": class_total_fee,
            "paid_fee": class_total_paid,
            "due_fee": class_total_due
        })

    data = {
        "school_summary": {
            "total_students": total_students,
            "total_fee": total_fee,
            "paid_fee": total_paid,
            "due_fee": total_due,
        },
        "class_summary": class_data
    }

    return Response(data)


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
    category_display_map = dict(Student._meta.get_field('category').choices)

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
@api_view(["GET"])
def fee_dashboard(request):
    filter_month = request.query_params.get("month")
    qs = FeeRecord.objects.all()

    # -------- Overall Summary --------
    total = qs.aggregate(
        total=Coalesce(Sum(F("total_amount") + F("late_fee"), output_field=FloatField()), Value(0.0))
    )["total"]
    paid = qs.aggregate(
        paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0))
    )["paid"]
    late_fee = qs.aggregate(
        late=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0))
    )["late"]

    due = max(0, total - paid)
    paid_percent = round((paid / total) * 100, 2) if total > 0 else 0.0
    due_percent = round((due / total) * 100, 2) if total > 0 else 0.0
    total_percent = round(paid_percent + due_percent, 2)

    overall_summary = {
        "total_amount": round(total, 2),
        "paid_amount": round(paid, 2),
        "due_amount": round(due, 2),
        "late_fee": round(late_fee, 2),
        "paid_percent": paid_percent,
        "due_percent": due_percent,
        "total_percent": total_percent
    }

    # -------- Monthly Summary --------
    # https://187gwsw1-7000.inc1.devtunnels.ms/d/fee-dashboard/?month=June
    monthly_qs = qs.filter(month__iexact=filter_month) if filter_month else qs
    monthly_data = (
        monthly_qs.values("month")
        .annotate(
            total_base=Coalesce(Sum("total_amount", output_field=FloatField()), Value(0.0)),
            late_fee=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0)),
            paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
        )
        .order_by("month")
    )

    monthly_summary = []
    for item in monthly_data:
        total = item["total_base"] + item["late_fee"]
        due = max(0, total - item["paid"])
        monthly_summary.append({
            "month": item["month"],
            "total_amount": round(total, 2),
            "paid_amount": round(item["paid"], 2),
            "due_amount": round(due, 2),
            "late_fee": round(item["late_fee"], 2),
            "paid_percent": round((item["paid"] / total) * 100, 2) if total > 0 else 0.0,
            "due_percent": round((due / total) * 100, 2) if total > 0 else 0.0,
            "late_fee_percent": round((item["late_fee"] / total) * 100, 2) if total > 0 else 0.0,
            "total_percent": 100.0
        })

    # -------- Payment Mode Distribution --------
    payment_data = FeeRecord.objects.values("payment_mode").annotate(count=Count("id"))
    total_payments = sum(item["count"] for item in payment_data)

    payment_distribution = [
        {
            "payment_mode": item["payment_mode"],
            "count": item["count"],
            "percentage": round((item["count"] / total_payments) * 100, 2) if total_payments else 0.0
        } for item in payment_data
    ]

    # -------- Top Defaulters (No Payment in Last 3 Months) --------

    # Defaulter Summary (based on dues in the last 3 months)
    three_months_ago = datetime.now().date() - timedelta(days=90)

    due_per_month = FeeRecord.objects.filter(
        payment_date__lt=three_months_ago
    ).values("student_id").annotate(
        total=Coalesce(Sum(F("total_amount") + F("late_fee"), output_field=FloatField()), Value(0.0)),
        paid=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
    ).annotate(
        due=F("total") - F("paid")
    ).filter(due__gt=0)

    defaulter_count = due_per_month.count()
    total_students = Student.objects.count()
    defaulter_percent = round((defaulter_count / total_students) * 100, 2) if total_students > 0 else 0.0
    
    
    # --------- Fee Defaulters (Based on Due Older Than 3 Months) ---------
    # three_months_ago = now().date() - timedelta(days=90)

    # # Get only FeeRecords from the last 3 months
    # recent_dues_qs = FeeRecord.objects.filter(payment_date__gte=three_months_ago)

    # # Annotate due per record
    # recent_dues_qs = recent_dues_qs.annotate(
    #     total_due=F('total_amount') + F('late_fee') - F('paid_amount')
    # ).filter(total_due__gt=0)

    # # Total number of fee records with due in last 3 months
    # defaulter_count = recent_dues_qs.values('student').distinct().count()

    # # Total number of students overall
    # total_students = Student.objects.count()

    # defaulter_percent = round((defaulter_count / total_students) * 100, 2) if total_students > 0 else 0.0

    # -------- Response --------
    return Response({
    "overall_summary": overall_summary,
    "monthly_summary": monthly_summary,
    "payment_mode_distribution": payment_distribution,
    "defaulter_summary": {
        "count": defaulter_count,
        "percent": defaulter_percent,
    }
})










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


class DocumentView(viewsets.ModelViewSet):
    queryset = Document.objects.prefetch_related('files', 'document_types')
    serializer_class = DocumentSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Validate files
        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "Files required"}, status=status.HTTP_400_BAD_REQUEST)

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
        if existing:
            serializer = self.get_serializer(existing, data=data, partial=True)
            existing.files.all().delete()
            action = 'replaced'
        else:
            serializer = self.get_serializer(data=data)
            action = 'created'

        serializer.is_valid(raise_exception=True)
        doc = serializer.save()

        # Save all uploaded files
        for file in files:
            File.objects.create(document=doc, file=file)

        return Response({
            'status': action,
            'document': self.get_serializer(doc, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)

    def _find_existing_document(self, data):
        """Helper method to find existing document matching criteria"""
        filter_params = {
            **{f: data.get(f) for f in ['student', 'teacher', 'guardian', 'office_staff'] 
               if data.get(f) is not None}
        }
        
        # If identities exist in data, include them in filter
        if data.get('identities'):
            filter_params['identities'] = data['identities']
        
        for doc in Document.objects.filter(**filter_params).prefetch_related('document_types'):
            if set(doc.document_types.values_list('id', flat=True)) == set(map(int, data['document_types'])):
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

# As of 04June2025 at 12:15 AM
# Re-implementation of Fee module based on the provided fee card
from django.db.models import Q
from collections import OrderedDict, defaultdict



class FeeTypeView(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer


class YearLevelFeeView(viewsets.ModelViewSet):
    serializer_class = YearLevelFeeSerializer

    def get_queryset(self):
        qs = YearLevelFee.objects.select_related('year_level', 'fee_type')
        fee_id = self.request.query_params.get('id')
        if fee_id:
            qs = qs.filter(id=fee_id)
        return qs

    # def get_queryset(self):           # just commneted as of 27june25 at 02:47 PM
    #     return YearLevelFee.objects.select_related('year_level', 'fee_type')
    
    # def get_queryset(self):         # GET /api/year-level-fee/?id=3
    #     queryset = YearLevelFee.objects.select_related('year_level', 'fee_type')
    #     fee_id = self.request.query_params.get('id', None)

    #     if fee_id is not None:
    #         queryset = queryset.filter(id=fee_id)

    #     return queryset
    

    def list(self, request, *args, **kwargs):       # GET /api/year-level-fee/
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        grouped_fees = YearLevelFeeSerializer.group_by_year_level(serializer.data)
        return Response(grouped_fees)

    def retrieve(self, request, pk=None):       # GET /api/year-level-fees/2/
        queryset = self.get_queryset().filter(year_level__id=pk)
        if not queryset.exists():
            return Response({"detail": "Not found."}, status=404)

        serializer = self.get_serializer(queryset, many=True)
        grouped_fees = YearLevelFeeSerializer.group_by_year_level(serializer.data)
        return Response(grouped_fees[0] if grouped_fees else {})
    
    

from twilio.rest import Client 

def send_whatsapp_message(message_text):
    account_sid = 'AC75f0880296f2c1377b2ca30442bbd3e1'
    auth_token = '01dfff8731923c8e91e47b469f533fd5'
    twilio_whatsapp_number = 'whatsapp:+14155238886'
    
    phone_numbers = [
       '+918109145639',
        # '+918847418400',
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

#discount for students-----------
class FeeDiscountView(viewsets.ModelViewSet):
    queryset = FeeDiscount.objects.all()
    serializer_class = FeeDiscountSerializer
    # permission_classes = [IsAuthenticated,IsDirector]


# from director.permission import FeeRecordPermission
from rest_framework.filters import SearchFilter  # (agar already import nahi hai)
from django.db.models import Q  # (agar already import nahi hai)


# Fee Record View
# https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/
class FeeRecordView(viewsets.ModelViewSet):
    serializer_class = FeeRecordSerializer
    queryset = FeeRecord.objects.all()
    # permission_classes = [FeeRecordPermission]
    filter_backends = [SearchFilter]
    permission_classes = [IsAuthenticated]
    # Enables search using ?search=something
    search_fields = [
        'remarks',
        'receipt_number',
        'student__user__first_name',
        'student__user__last_name',
        'year_level_fees__year_level__level_name',
    ]
    
    # https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/?year_level=6
    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()

        #  Role-based visibility
        if hasattr(user, "director") or hasattr(user, "officestaff") or user.is_staff or user.is_superuser:
            pass  # full access
        elif hasattr(user, "teacher"):
            # only teacher's assigned YearLevels
            teacher_year_levels = user.teacher.teacheryearlevel_set.values_list("year_level_id", flat=True)
            qs = qs.filter(student__student_year_levels__level_id__in=teacher_year_levels)
        elif hasattr(user, "student"):
            # only own records
            qs = qs.filter(student=user.student)
        elif hasattr(user, "guardian_relation"):
            children_ids = user.guardian_relation.studentguardian.values_list("student_id", flat=True)
            qs = qs.filter(student_id__in=children_ids)
        else:
            qs = qs.none()

        # Keep your existing filters
        request = self.request
        
        month = request.query_params.get('month')
        if month:
            qs = qs.filter(month=month)

        school_year = request.query_params.get('school_year')
        if school_year:
            qs = qs.filter(school_year__year__year_name = school_year)

        student_id = request.query_params.get('student_id')
        if student_id:
            qs = qs.filter(student_id=student_id)

        year_level_id = request.query_params.get('year_level')
        if year_level_id:
            qs = qs.filter(year_level_fees__year_level__id=year_level_id)
    
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            parts = search.split(" ")
            if len(parts) > 1:
                qs = qs.filter(
                    Q(student__user__first_name__icontains=parts[0]) &
                    Q(student__user__last_name__icontains=' '.join(parts[1:]))
                )
            else:
                qs = qs.filter(
                    Q(student__user__first_name__icontains=search) |
                    Q(student__user__last_name__icontains=search)
                )
    
        return qs.distinct()

    # removed commented or unnecessary code from line 1906 - 2266
        # commented as of 26Aug25 at 04:34 PM

    # Added as of 26Aug25 at 04:34 PM
    # @action(detail=False, methods=["get"], url_path="fee-preview")
    # def preview(self, request):
    #     student_id = request.query_params.get("student_id")
    #     month = request.query_params.get("month")

    #     if not student_id or not month:
    #         return Response({"detail": "student_id and month are required"}, status=400)

    #     try:
    #         student = Student.objects.get(id=student_id)
    #     except Student.DoesNotExist:
    #         return Response({"detail": "Student not found"}, status=404)

    #     # Latest active year level
    #     student_year_level = (
    #         StudentYearLevel.objects
    #         .filter(student=student)
    #         .order_by("-year")
    #         .first()
    #     )
    #     if not student_year_level:
    #         return Response({"detail": "No year level found for this student."}, status=404)

    #     # All year-level fees
    #     year_level_fees = YearLevelFee.objects.filter(year_level=student_year_level.level)

    #     # Paid fee records for this student & school year
    #     paid_fees = FeeRecord.objects.filter(
    #         student=student,
    #         school_year__year=student_year_level.year
    #     )

    #     # Admission fees → only once per year
    #     admission_paid_fee_ids = paid_fees.filter(
    #         year_level_fees__fee_type__name__iexact="admission fee"
    #     ).values_list("year_level_fees", flat=True)

    #     # Tuition fees (monthly) → must match same month
    #     monthly_paid_fee_ids = YearLevelFee.objects.filter(
    #         feerecord__in=paid_fees,
    #         feerecord__month__iexact=month,
    #         fee_type__name__iexact="tuition fee"
    #     ).values_list("id", flat=True)

    #     # Exam fees → must match same month
    #     exam_paid_fee_ids = paid_fees.filter(
    #         month=month,
    #         year_level_fees__fee_type__name__iexact="exam fee"
    #     ).values_list("year_level_fees", flat=True)

    #     # Transport fees → must match same month
    #     transport_paid_fee_ids = paid_fees.filter(
    #         month=month,
    #         year_level_fees__fee_type__name__iexact="transport fee"
    #     ).values_list("year_level_fees", flat=True)

    #     # Serialize fees
    #     serializer = YearLevelFeeSerializer(year_level_fees, many=True, context={"student": student})
    #     grouped_fees = YearLevelFeeSerializer.group_by_year_level(serializer.data)

    #     today = date.today()

    #     # --- Add status/late fee ---
    #     for group in grouped_fees:
    #         new_fees_list = []  # Create a new list to hold the modified fee dictionaries
    #         for fee in group["fees"]:
    #             fee_id = fee["id"]
    #             fee_type = fee["fee_type"].lower()

    #             # --- HANDLING ADMISSION, TUITION, EXAM, TRANSPORT ---
    #             if (fee_type == "admission fee" and fee_id in admission_paid_fee_ids) or \
    #             (fee_type == "tuition fee" and fee_id in monthly_paid_fee_ids) or \
    #             (fee_type == "exam fee" and fee_id in exam_paid_fee_ids) or \
    #             (fee_type == "transport fee" and fee_id in transport_paid_fee_ids):

    #                 # Already Paid → minimal response
    #                 new_fee = {
    #                     "fee_type": fee_type.title(),
    #                     "id": fee_id,
    #                     "status": "Already Paid"
    #                 }
    #                 new_fees_list.append(new_fee)

    #             else:
    #                 # Pending → include amounts
    #                 fee["amount"] = str(fee.get("amount", "0"))
    #                 fee["final_amount"] = str(fee.get("final_amount", "0"))
    #                 fee["status"] = "Pending"

    #                 # Late Fee (only for Tuition Fee)
    #                 if fee_type == "tuition fee" and today.day > 15:
    #                     fee["late_fee"] = 25

    #                 new_fees_list.append(fee)

    #         group["fees"] = new_fees_list

    #     return Response(grouped_fees)

    @action(detail=False, methods=["get"], url_path="fee-preview")
    def preview(self, request):
        student_id = request.query_params.get("student_id")
        month = request.query_params.get("month")

        if not student_id or not month:
            return Response({"detail": "student_id and month are required"}, status=400)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"detail": "Student not found"}, status=404)

        # Latest active year level
        student_year_level = (
            StudentYearLevel.objects
            .filter(student=student)
            .order_by("-year")
            .first()
        )
        if not student_year_level:
            return Response({"detail": "No year level found for this student."}, status=404)

        # All year-level fees
        year_level_fees = YearLevelFee.objects.filter(year_level=student_year_level.level)

        # Paid fee records for this student & school year
        paid_fees = FeeRecord.objects.filter(
            student=student,
            school_year__year=student_year_level.year
        )

        # Admission fees → only once per year
        admission_paid_fee_ids = paid_fees.filter(
            year_level_fees__fee_type__name__iexact="admission fee"
        ).values_list("year_level_fees", flat=True)

        # Tuition fees (monthly)
        tuition_records = paid_fees.filter(
            month=month,
            year_level_fees__fee_type__name__iexact="tuition fee"
        )
        monthly_paid_fee_ids = tuition_records.values_list("year_level_fees", flat=True)

        # Exam fees
        exam_paid_fee_ids = paid_fees.filter(
            month=month,
            year_level_fees__fee_type__name__iexact="exam fee"
        ).values_list("year_level_fees", flat=True)

        # Transport fees
        transport_paid_fee_ids = paid_fees.filter(
            month=month,
            year_level_fees__fee_type__name__iexact="transport fee"
        ).values_list("year_level_fees", flat=True)

        # Serialize fees
        serializer = YearLevelFeeSerializer(year_level_fees, many=True, context={"student": student})
        grouped_fees = YearLevelFeeSerializer.group_by_year_level(serializer.data)

        today = date.today()

        # --- Add status/amounts ---
        for group in grouped_fees:
            new_fees_list = []
            for fee in group["fees"]:
                fee_id = fee["id"]
                fee_type = fee["fee_type"].lower()
                new_fee = {"id": fee_id, "fee_type": fee["fee_type"]}

                # ADMISSION
                if fee_type == "admission fee":
                    if fee_id in admission_paid_fee_ids:
                        new_fee["status"] = "Already Paid"
                    else:
                        new_fee["final_amount"] = str(fee.get("final_amount", "0"))
                        new_fee["status"] = "Pending"

                # TUITION
                elif fee_type == "tuition fee":
                    if fee_id in monthly_paid_fee_ids:
                        latest_record = tuition_records.order_by("-id").first()
                        if latest_record:
                            if latest_record.due_amount == 0:
                                new_fee["status"] = "Already Paid"
                            elif latest_record.paid_amount > 0:
                                # new_fee["paid_amount"] = str(latest_record.paid_amount)
                                new_fee["due_amount"] = str(latest_record.due_amount)
                                new_fee["status"] = "Partially Paid"
                            else:
                                new_fee["final_amount"] = str(fee.get("final_amount", "0"))
                                new_fee["status"] = "Pending"
                    else:
                        new_fee["final_amount"] = str(fee.get("final_amount", "0"))
                        new_fee["status"] = "Pending"

                    # Apply late fee only if today is past 15th and fee isn't fully paid
                    if today.day > 15 and new_fee["status"] in ["Partially Paid", "Pending"]:
                        new_fee["late_fee"] = 25

                # EXAM
                elif fee_type == "exam fee":
                    if fee_id in exam_paid_fee_ids:
                        new_fee["status"] = "Already Paid"
                    else:
                        new_fee["final_amount"] = str(fee.get("final_amount", "0"))
                        new_fee["status"] = "Pending"

                # TRANSPORT
                elif fee_type == "transport fee":
                    if fee_id in transport_paid_fee_ids:
                        new_fee["status"] = "Already Paid"
                    else:
                        new_fee["final_amount"] = str(fee.get("final_amount", "0"))
                        new_fee["status"] = "Pending"

                new_fees_list.append(new_fee)
            group["fees"] = new_fees_list

        return Response(grouped_fees)
    
   

    

        
    @action(detail=False, methods=['post'], url_path='submit_single_multi_month_fees')
    def submit_single_multi_month_fees(self, request):
        student_id = request.data.get('student_id')
        months = request.data.get('months', [])
        year_level_fees = request.data.get('year_level_fees', [])
        paid_amount = Decimal(request.data.get('paid_amount', "0.00"))
        payment_mode = request.data.get('payment_mode')
        remarks = request.data.get('remarks')
        received_by = request.data.get('received_by')
        
        admission = Admission.objects.filter(student_id=student_id).first()
        
        if admission and admission.is_rte and admission.rte_number:
            return Response(
                {"message": f"Student {admission.student.user.get_full_name()} belongs to RTE category, fees record not created."},
                status=status.HTTP_400_BAD_REQUEST
        )


        if not months or not isinstance(months, list):
            return Response({"error": "Months must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)

        receipt_number = FeeRecord().generate_unique_receipt_number()
        total_amount = Decimal("0.00")
        total_late_fee = Decimal("0.00")
        total_due = Decimal("0.00")
        saved_records = []

        for month in months:
            serializer = self.get_serializer(data={
                "student_id": student_id,
                "month": month,
                "year_level_fees": year_level_fees,
                "paid_amount": paid_amount,
                "payment_mode": payment_mode,
                "remarks": f"{remarks or ''} ({month})",
                "received_by": received_by,
                "receipt_number": receipt_number  
            })

            if serializer.is_valid():
                instance = serializer.save()
                total_amount += instance.total_amount
                total_late_fee += instance.late_fee
                total_due += instance.due_amount
                saved_records.append(instance)
            else:
                return Response({"month": month, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        # Use the first record as base
        first_record = saved_records[0]
        combined_response = {
            "id": first_record.id,
            "student": {
                "id": first_record.student.id,
                "name": first_record.student.user.get_full_name()
            },
            "months": months,
            "year_level_fees_grouped": FeeRecordSerializer(first_record).data["year_level_fees_grouped"],
            "total_amount": f"{total_amount:.2f}",
            "paid_amount": f"{paid_amount:.2f}",
            "due_amount": f"{total_due:.2f}",
            "payment_date": str(date.today()),
            "payment_mode": payment_mode,
            "is_cheque_cleared": False,
            "receipt_number": receipt_number,
            "late_fee": f"{total_late_fee:.2f}",
            "payment_status": "Paid" if total_due == 0 else "Unpaid",
            "remarks": remarks,
            "received_by": received_by
        }
        message_text = (
            f"Dear {first_record.student.user.get_full_name()},\n"
            f"Your fee for {', '.join(months)} month has been successfully recorded.\n"
            f"Receipt No: {receipt_number}\n"
            f"Total Amount: ₹{total_amount:.2f}\n"
            f"Paid Amount: ₹{paid_amount:.2f}\n"
            f"Due Amount: ₹{total_due:.2f}\n"
            f"Payment Mode: {payment_mode}\n"
            f"received_by: {received_by}\n"
            f"Thank you!"
        )
        send_whatsapp_message(message_text)

        return Response(combined_response, status=status.HTTP_200_OK)
    
    
    ### Razorpay custom views
    # https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/initiate-payment/
    ### using custom view 
    ### Added as of 12june25 at 02:20 PM
    @action(detail=False, methods=["post"], url_path="initiate-payment")
    def initiate_payment(self, request):
        serializer = FeeRecordRazorpaySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        validated_data = serializer.validated_data
        total = validated_data['total_amount']
        late_fee = validated_data['late_fee']
        paid_amount = validated_data['paid_amount']
        amount_to_collect = total + late_fee  # This is the full due amount, not necessarily what's paid

        receipt_number = generate_receipt_number()

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(paid_amount * 100),  # Razorpay expects amount in paise
            'currency': 'INR',
            'payment_capture': '1',
            'receipt': receipt_number
        })

        return Response({
            'razorpay_order_id': razorpay_order['id'],
            'total_amount': float(total),
            'late_fee': float(late_fee),
            'paid_amount': float(paid_amount),
            'currency': 'INR',
            'receipt_number': receipt_number
        }, status=status.HTTP_200_OK)

    
    ### just added as of 13june25 at 11:21 AM
    # https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/confirm-payment/
    ### ------------------------------------- ###
    # working completely fine just need to add complete fee record adding updated code here
    @action(detail=False, methods=["post"], url_path="confirm-payment")
    def confirm_payment(self, request):
        data = request.data
        required_fields = [
            "razorpay_payment_id",
            "razorpay_order_id",
            "razorpay_signature_id",
            "student_id",
            "month",
            "year_level_fees",
            "paid_amount",
            "payment_mode",
            "received_by"
        ]
        missing = [field for field in required_fields if field not in data]

        if missing:
            return Response({"error": f"Missing required fields: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Verify Razorpay Signature
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature_id"]
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment verification failed"}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Save FeeRecord
        serializer = FeeRecordRazorpaySerializer(data=data)
        if serializer.is_valid():
            instance = serializer.save()

            # Serialize with full FeeRecordSerializer to return complete info
            # full_data = FeeRecordSerializer(instance).data    # fix the issue 04Sep25 at 03:43 PM
            full_data = FeeRecordSerializer(instance, context={'request': request}).data

            return Response({
                "message": "Payment successful and FeeRecord saved.",
                "fee_record": full_data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    # corrected amount issue as of 19June25 at 02:50 PM
    # https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/student-fee-summary/?year_level=5
    @action(detail=False, methods=["get"], url_path="student-fee-summary")
    def student_fee_summary(self, request):
        year_level = request.query_params.get("year_level")
        search = request.query_params.get("search", "").strip()

        qs = self.get_queryset()
        filters = Q()

        if year_level:
            filters &= Q(student__student_year_levels__level__id=year_level)

        if search:
            filters &= (
                Q(student__user__first_name__icontains=search) |
                Q(student__user__last_name__icontains=search)
            )

        qs = qs.filter(filters).distinct()

        summary = (
            qs.values(
                "student_id",
                "student__user__first_name",
                "student__user__last_name",
                "student__student_year_levels__level__level_name"
            )
            .annotate(
                total_amount=Coalesce(Sum("total_amount", output_field=FloatField()), Value(0.0)),
                paid_amount=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
                late_fee=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0))
            )
        )

        result = []
        for item in summary:
            total = item["total_amount"]# + item["late_fee"]#is se do baar late fee add ho rahi he
            due = max(0, total - item["paid_amount"])

            result.append({
                "student_id": item["student_id"],
                "student_name": f"{item['student__user__first_name']} {item['student__user__last_name']}",
                "year_level": item["student__student_year_levels__level__level_name"],
                "total_amount": float(total),
                "paid_amount": float(item["paid_amount"]),
                "due_amount": float(due),
                "late_fee": float(item["late_fee"])  #  now included
            })

        return Response(result, status=status.HTTP_200_OK)

    # corrected amount issue as of 19June25 at 02:50 PM
    # https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/monthly-summary/?year_level=2&month=June
    @action(detail=False, methods=["get"], url_path="monthly-summary")
    def monthly_summary(self, request):
        month = request.query_params.get("month", "").strip()
        year_level = request.query_params.get("year_level", "").strip()
        search = request.query_params.get("search", "").strip()
        school_year = request.query_params.get("school_year", "").strip()

        qs = self.get_queryset()
        filters = Q()

        if month:
            filters &= Q(month__iexact=month)
        if school_year:    
            filters &= Q(school_year__year__year_name__iexact=school_year)
        if year_level.isdigit():
            filters &= Q(student__student_year_levels__level__id=year_level)
        elif search:
            filters &= Q(student__student_year_levels__level__level_name__icontains=search)

        qs = qs.filter(filters).distinct()

        if not qs.exists():
            return Response({"detail": "No records found."}, status=status.HTTP_404_NOT_FOUND)
        

        summary = (
            qs.values(
                "month",
                "school_year__year__year_name",
                "student__user__first_name",
                "student__user__last_name",
                "student__student_year_levels__level__level_name"
            )
            .annotate(
                total_amount=Coalesce(Sum("total_amount", output_field=FloatField()), Value(0.0)),
                paid_amount=Coalesce(Sum("paid_amount", output_field=FloatField()), Value(0.0)),
                late_fee=Coalesce(Sum("late_fee", output_field=FloatField()), Value(0.0))
            )
        )
        # print(summary)
        formatted_summary = []
        for item in summary:
            total = item["total_amount"] #+ item["late_fee"]#is se do baar late fee add ho rahi he
            due = max(0, total - item["paid_amount"])
            
            formatted_summary.append({
                "month": item["month"],
                "school_year": item["school_year__year__year_name"] or "N/A",
                "student_name": f"{item['student__user__first_name']} {item['student__user__last_name']}",
                "year_level": item["student__student_year_levels__level__level_name"],
                "total_amount": float(total),
                "paid_amount": float(item["paid_amount"]),
                "due_amount": float(due),
                "late_fee": float(item["late_fee"])  #  now included
            })

        return Response(formatted_summary, status=status.HTTP_200_OK)
    
    
    # retrieving students who dont have fee record at all
    @action(detail=False, methods=['get'], url_path="defaulters")
    def defaulters(self, request):
        # Last payment date for each student
        last_payment_subquery = FeeRecord.objects.filter(
            student=OuterRef('pk')
        ).order_by('-payment_date').values('payment_date')[:1]

        students = Student.objects.annotate(
            last_payment=Subquery(last_payment_subquery, output_field=DateField()),
            total=Coalesce(
                Sum(
                    ExpressionWrapper(
                        Cast(F('feerecord__total_amount'), output_field=DecimalField(max_digits=10, decimal_places=2)) +
                        Cast(F('feerecord__late_fee'), output_field=DecimalField(max_digits=10, decimal_places=2)),
                        output_field=DecimalField(max_digits=10, decimal_places=2)
                    )
                ),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ),
            paid=Coalesce(
                Sum('feerecord__paid_amount'),
                Value(0),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )
        )

        defaulters_list = []
        for s in students:
            # CASE 1: No records (total = 0, paid = 0)
            # CASE 2: Has dues (paid < total)
            has_dues = s.total > s.paid
            no_records = s.total == 0 and s.paid == 0 and s.last_payment is None

            if no_records or has_dues:
                due = max(s.total - s.paid, 0)
                defaulters_list.append({
                    'id': s.id,
                    'name': getattr(s, 'name', f"{s.user.first_name} {s.user.last_name}"),
                    'total': float(s.total),
                    'paid': float(s.paid),
                    'due': float(due),
                    'last_payment': s.last_payment.isoformat() if s.last_payment else None
                })

        return Response(defaulters_list)

    # Added as of 30June25 at 01:46 PM
    # Fee card API for individual student
    # https://187gwsw1-7000.inc1.devtunnels.ms/d/fee-record/student-fee-card/?student_id=12
    
    @action(detail=False, methods=["get"], url_path="student-fee-card")
    def student_fee_card(self, request):
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response({"error": "student_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({"error": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get year level
        student_year_level = student.student_year_levels.first()
        year_level_name = student_year_level.level.level_name if student_year_level and student_year_level.level else "N/A"

        # Fetch all fee records
        fee_qs = FeeRecord.objects.filter(student=student).prefetch_related("year_level_fees__fee_type")

        # Group data by month
        monthly_data = defaultdict(list)
        for fee in fee_qs:
            monthly_data[fee.month].append(fee)

        result = {
            "student_id": student.id,
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "year_level": year_level_name,
            "monthly_summary": []
        }

        for month, fees in monthly_data.items():
            total_amount = sum((f.total_amount or 0) + (f.late_fee or 0) for f in fees)
            paid_amount = sum(f.paid_amount or 0 for f in fees)
            due_amount = max(Decimal("0.00"), total_amount - paid_amount)

            # Type-wise summary
            type_summary = defaultdict(lambda: {"amount": Decimal("0.00"), "paid": Decimal("0.00")})

            for f in fees:
                for ylf in f.year_level_fees.all():
                    fee_type = ylf.fee_type.name if ylf.fee_type else "Unknown"
                    amount = ylf.amount or 0
                    share_ratio = amount / f.total_amount if f.total_amount else 0

                    # Split late fee and paid_amount proportionally among all year_level_fees
                    type_summary[fee_type]["amount"] += amount
                    type_summary[fee_type]["paid"] += (f.paid_amount or 0) * share_ratio

            result["monthly_summary"].append({
                "month": month,
                "total_amount": float(total_amount),
                # "paid_amount": float(paid_amount),
                "due_amount": float(due_amount),
                "fee_type": [
                    {
                        "type": ft,
                        "amount": float(val["amount"]),
                        # "paid": round(float(val["paid"]), 2)
                    } for ft, val in type_summary.items()
                ]
            })

        return Response(result, status=status.HTTP_200_OK)


    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated],url_path="student_unpaid_fees")
    def student_unpaid_fees(self, request):
        user = request.user
        roles = [role.name.lower() for role in user.role.all()]
        student_id = request.query_params.get("student_id")

        if "director" in roles or "office staff" in roles:
            if student_id:
                queryset = FeeRecord.objects.filter(payment_status="Unpaid", student_id=student_id)
            else:
                queryset = FeeRecord.objects.filter(payment_status="Unpaid")


        elif "teacher" in roles:
            teacher_instance = get_object_or_404(Teacher, user=user)

            assigned_class_ids = TeacherYearLevel.objects.filter(
                teacher=teacher_instance
            ).values_list("year_level_id", flat=True)

            if student_id:
                try:
                    student_yl = StudentYearLevel.objects.select_related("student", "level").get(id=student_id)
                except StudentYearLevel.DoesNotExist:
                    return Response({"detail": "Student not found."}, status=404)

                if student_yl.level.id not in assigned_class_ids:
                    return Response({"detail": "You are not allowed to view this student's data."}, status=403)

                queryset = FeeRecord.objects.filter(
                    payment_status="Unpaid",
                    student=student_yl.student
                )

            else:
                student_ids = StudentYearLevel.objects.filter(
                    level_id__in=assigned_class_ids
                ).values_list("student_id", flat=True)

                queryset = FeeRecord.objects.filter(
                    payment_status="Unpaid",
                    student_id__in=student_ids
                )


        elif "student" in roles:
            if "student_id" in request.query_params:
                return Response({"detail": "You are not allowed to provide student_id."}, status=400)

            student = get_object_or_404(Student, user=user)
            queryset = FeeRecord.objects.filter(
                payment_status="Unpaid",
                student=student
            )


        elif "guardian" in roles:
            if "student_id" in request.query_params:
                return Response({"detail": "You are not allowed to provide student_id."}, status=400)
            guardian = get_object_or_404(Guardian, user=user)
            student_ids = StudentGuardian.objects.filter(guardian=guardian).values_list("student_id", flat=True)
            queryset = FeeRecord.objects.filter(
                payment_status="Unpaid", student_id__in=student_ids
            )

        else:
            return Response({"detail": "Permission denied."}, status=403)

        # serializer = FeeRecordSerializer(queryset, many=True) 
        # return Response(serializer.data)

        serializer = FeeRecordSerializer(queryset, many=True, context={"request": request})
        notifications = []
        for fee_record in queryset:
            student = fee_record.student
            msg = (
                f" Dear {student.user.get_full_name()},\n"
                f"Your fee for {fee_record.month} is still UNPAID.\n"
                f"Total Amount: ₹{fee_record.total_amount}\n"
                f"Paid: ₹{fee_record.paid_amount}\n"
                f"Due: ₹{fee_record.due_amount}\n"
                f"Please clear it at the earliest."
            )
            # WhatsApp notification bhejna
            response = send_whatsapp_message(msg)   # <-- apka existing function
            notifications.append({
                "student": student.user.get_full_name(),
                "month": str(fee_record.month),
                "due_amount": str(fee_record.due_amount),
                "response": response
            })
        # -------------------------------------------------------

        return Response({
            "unpaid_fees": serializer.data,
            "notifications": notifications
        })



    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="overall_unpaid_fees")
    def overall_unpaid_fees(self, request):
        user = request.user
        roles = [role.name.lower() for role in user.role.all()]

        if not any(role in roles for role in ["director", "teacher", "office staff"]):
            return Response({"detail": "You do not have permission to access this data."}, status=status.HTTP_403_FORBIDDEN)

        class_id = request.query_params.get("class_id", "").strip()
        month = request.query_params.get("month", "").strip()

        unpaid_fee_records = []

        student_levels = StudentYearLevel.objects.all().select_related("student", "level")

        if "teacher" in roles:
            try:
                teacher = Teacher.objects.get(user=user)
                teacher_classes = TeacherYearLevel.objects.filter(teacher=teacher).values_list("year_level_id", flat=True)
            except Teacher.DoesNotExist:
                return Response({"detail": "Teacher not found."}, status=status.HTTP_404_NOT_FOUND)
            except TeacherYearLevel.DoesNotExist:
                return Response({"detail": "Assigned class for teacher not found."}, status=status.HTTP_404_NOT_FOUND)

            student_levels = student_levels.filter(level_id__in=teacher_classes)

        if class_id:
            student_levels = student_levels.filter(level_id=class_id)

        for student_level in student_levels:
            student = student_level.student

            fee_records = FeeRecord.objects.filter(
                student=student,
                payment_status="unpaid"
            ).prefetch_related(
                "year_level_fees__year_level",
                "year_level_fees__fee_type"
            )

            if month:
                fee_records = fee_records.filter(month__iexact=month)

            for record in fee_records:
                grouped_fees = {}
                for ylf in record.year_level_fees.all():
                    level_name = ylf.year_level.level_name
                    if level_name not in grouped_fees:
                        grouped_fees[level_name] = []
                    grouped_fees[level_name].append({
                        "id": ylf.id,
                        "fee_type": ylf.fee_type.name,
                        "amount": str(ylf.amount)
                    })

                grouped_fees_list = [
                    {"year_level": level, "fees": fees}
                    for level, fees in grouped_fees.items()
                ]

                unpaid_fee_records.append({
                    "id": record.id,
                    "student": {
                        "id": student.id,
                        "name": str(student)
                    },
                    "month": record.month,
                    "year_level_fees_grouped": grouped_fees_list,
                    "total_amount": str(record.total_amount),
                    "paid_amount": str(record.paid_amount),
                    "due_amount": str(record.due_amount),
                    "payment_date": record.payment_date,
                    "payment_mode": record.payment_mode,
                    "is_cheque_cleared": record.is_cheque_cleared,
                    "receipt_number": record.receipt_number,
                    "late_fee": str(record.late_fee),
                    "payment_status": record.payment_status,
                    "remarks": record.remarks,
                    "received_by": record.received_by,
                })

        return Response(unpaid_fee_records, status=status.HTTP_200_OK)


    @action(detail=False, methods=["get"], url_path="highest_dues_students")
    def highest_dues_students(self, request):
        user = request.user
        roles = [role.name.lower() for role in user.role.all()]

        if not any(role in roles for role in ["director", "teacher", "office staff"]):
            return Response({"detail": "You do not have permission to access this data."})

        class_id = request.query_params.get("class_id")
        month = request.query_params.get("month")
        min_due = request.query_params.get("min_due_amount")
        max_due = request.query_params.get("max_due_amount")
        # top = request.query_params.get("top")

        queryset = FeeRecord.objects.filter(payment_status="unpaid")
        print("queryset : ",queryset)
        class_id = request.query_params.get("class_id")
        if class_id:
            class_id = class_id.strip()  
            student_ids = StudentYearLevel.objects.filter(level_id=class_id).values_list("student_id", flat=True)
            print("student_ids:", list(student_ids))  
            queryset = queryset.filter(student_id__in=student_ids)
        if month:
            queryset = queryset.filter(month=month)

        if min_due:
            try:
                queryset = queryset.filter(due_amount__gte=float(min_due))
            except ValueError:
                return Response({"detail": "min_due_amount must be a number."})

        if max_due:
            try:
                queryset = queryset.filter(due_amount__gte=float(max_due))
            except ValueError:
                return Response({"detail": "max_due_amount must be a number."})

        queryset = queryset.order_by("due_amount")

        # if top:
        #     try:
        #         top = int(top)
        #         queryset = queryset[:top]
        #     except ValueError:
        #         return Response({"detail": "top must be an integer."})

        # data = []
        # for record in queryset:
        #     for ylf in record.year_level_fees.all():
        #         data.append({
        #             "student_id": record.student.id,
        #             "student_name": str(record.student),
        #             "class_name": ylf.year_level.level_name,  
        #             "month": record.month,
        #             "due_amount": str(record.due_amount),
        #             "total_amount": str(record.total_amount),
        #             "paid_amount": str(record.paid_amount),
        #         })
        # return Response(data, status=status.HTTP_200_OK)

        data = []
        for record in queryset:
            grouped_fees = {}
            for ylf in record.year_level_fees.all():
                level_name = ylf.year_level.level_name
                if level_name not in grouped_fees:
                    grouped_fees[level_name] = []
                grouped_fees[level_name].append({
                    "id": ylf.id,
                    "fee_type": ylf.fee_type.name,
                    "amount": str(ylf.amount)
                })

            grouped_fees_list = [
                {"year_level": level, "fees": fees}
                for level, fees in grouped_fees.items()
            ]

            data.append({
                "id": record.id,
                "student": {
                    "id": record.student.id,
                    "name": str(record.student)
                },
                "month": record.month,
                "year_level_fees_grouped": grouped_fees_list,
                "total_amount": str(record.total_amount),
                "paid_amount": str(record.paid_amount),
                "due_amount": str(record.due_amount),
                "payment_date": record.payment_date,
                "payment_mode": record.payment_mode,
                "is_cheque_cleared": record.is_cheque_cleared,
                "receipt_number": record.receipt_number,
                "late_fee": str(record.late_fee),
                "payment_status": record.payment_status,
                "remarks": record.remarks,
                "received_by": record.received_by,
            })
        return Response(data)    
    


### --------------------- Income Distribution Dashboard API (Guardian name and student name and id added) --------------------------- ###
### ------------------- As of 03 JUly at 12:35 --------------- ###   By daniyal

@api_view(["GET"])
def guardian_income_distribution_with_student(request):
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

@api_view(["POST"])
# @permission_classes([RoleBasedUserManagementPermission])
def deactivate_user(request):
    deactivate_user.api_section = "deactivate_user" 
    try:
        with transaction.atomic():
            user_id = request.data.get("user_id")
            user = User.objects.all_including_inactive().get(id=user_id)
            if not user.is_active:
                return Response({"error": "User already deactivated"})
            user.is_active = False
            user.deactivation_reason = request.data.get('reason', '')
            user.deactivation_date = timezone.now()
            user.reactivation_date = None
            user.save()
            
            # Handle Student    (classes [clear], admission, feeRecord, document, )
            student = getattr(user, 'student', None)
            if student is not None:
                student = user.student
                student.is_active = False
                student.save()
                # Clear Student.classes and StudentYearLevel 
                student.classes.clear()
                # Clear StudentYearLevel (handle missing studenyearlevel_set)
                try:
                    StudentYearLevel.objects.filter(student=student).delete()
                except AttributeError:
                    pass  # No StudentYearLevel relationship

                # Clear related Admissions
                admissions = Admission.objects.filter(student=student)
                for admission in admissions:
                    admission.is_active = False
                    admission.save()
                # Clear related FeeRecords
                fee_records = FeeRecord.objects.filter(student=student)
                for fee_record in fee_records:
                    fee_record.is_active = False
                    fee_record.save()
                # Clear related Documents
                documents = Document.objects.filter(student=student)
                for document in documents:
                    document.is_active = False
                    document.save()
                # Deactivate related Addresses
                addresses = Address.objects.filter(user=user)
                for address in addresses:
                    address.is_active = False
                    address.save()
                # Deactivate Banking Details
                bank_details = BankingDetail.objects.filter(user=user)
                for bank_detail in bank_details:
                    bank_detail.is_active = False
                    bank_detail.save()    

            # Handle Guardian   (Student guardian relation [clear], address, docs)
            guardian = getattr(user, 'guardian_relation', None)
            if guardian is not None:
                guardian = user.guardian_relation
                guardian.is_active = False
                guardian.save()
                # Clear StudentGuardian connections
                student_guardians = StudentGuardian.objects.filter(guardian=guardian)
                for sg in student_guardians:
                    sg.delete()  # Clear the relationship
                # Deactivate related Addresses
                addresses = Address.objects.filter(user=user)
                for address in addresses:
                    address.is_active = False
                    address.save()
                # Clear related Documents
                documents = Document.objects.filter(guardian=guardian)
                for document in documents:
                    document.is_active = False
                    document.save() 
                
            # Handle Teacher  (classPeriod [clear {M2M}], address, docs)
            teacher = getattr(user, 'teacher', None)
            if teacher is not None:
                teacher = user.teacher
                teacher.is_active = False
                teacher.save()

                # Clear TeacherYearLevel connections
                teacher.year_levels.clear()
                # Remove teacher from ClassPeriod assignments
                class_periods = ClassPeriod.objects.filter(teacher=teacher)
                for cp in class_periods:
                    cp.teacher = None  # Set to None to remove assignment
                    cp.save()
                ClassPeriod.objects.filter(teacher=teacher).delete()
                # Deactivate related Addresses
                addresses = Address.objects.filter(user=user)
                for address in addresses:
                    address.is_active = False
                    address.save()
                # Clear related Documents
                documents = Document.objects.filter(teacher=teacher)
                for document in documents:
                    document.is_active = False
                    document.save()    
                    

            # Handle OfficeStaff  ([student,teacher,admission {clear M2M}, address, docs])
            office_staff = getattr(user, 'office_staff', None)
            if office_staff is None:
                # Attempt to fetch OfficeStaff directly to confirm relation
                try:
                    office_staff = OfficeStaff.objects.get(user=user)
                except OfficeStaff.DoesNotExist:
                    print(f"No OfficeStaff found for user {user.id} via query")
            else:
                try:
                    office_staff.is_active = False
                    office_staff.save()
                    # Clear ManyToMany relationships
                    office_staff.student.clear()
                    office_staff.teacher.clear()
                    office_staff.admissions.clear()
                    # Deactivate related Addresses
                    addresses = Address.objects.filter(user=user)
                    for address in addresses:
                        address.is_active = False
                        address.save()
                    # Clear related Documents
                    documents = Document.objects.filter(office_staff=office_staff)
                    for document in documents:
                        document.is_active = False
                        document.save()
                except Exception as e:
                    return Response({"error": f"Failed to deactivate OfficeStaff: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Handle Director (if needed)
            director = getattr(user, 'director', None)
            if director is not None:
                director = user.director
                director.is_active = False
                director.save()
                # Deactivate related Addresses
                addresses = Address.objects.filter(user=user)
                for address in addresses:
                    address.is_active = False
                    address.save()

            # log termination
            UserStatusLog.objects.create(user=user, status='TERMINATED', reason=user.deactivation_reason)
            serializer = UserSerializer(user)
            return Response({
                "message": f"User {user.id} has been successfully terminated.",
                "user_id": user.id,
                "data": serializer.data})
    except User.DoesNotExist:
        return Response({"error": "User not found"})
 
### -------------------------------------------------------------- ###

# *************** Reactivation of the User *******************************************************
from django.core.exceptions import ObjectDoesNotExist

@api_view(["POST"])
# @permission_classes([RoleBasedUserManagementPermission])
def reactivate_user(request):
    reactivate_user.api_section = "reactivate_user" 
    try:
        with transaction.atomic():
            user_id = request.data.get("user_id")
            user = User.objects.all_including_inactive().get(id=user_id)
            if user.is_active:
                return Response({"error": "User already active"})
            user.is_active = True
            user.deactivation_reason = None
            user.reactivation_date = timezone.now()
            user.save()
            
            # Handle Student    ([classes {make}, studentyearlevel, studentguardian] , admission, feeRecord, document, address,
            # banking details )
            student = getattr(user, 'student', None)
            if student is not None:
                student = user.student
                student.is_active = True
                student.save()

                # retrieve related Admissions
                admissions = Admission.objects.all_including_inactive().filter(student=student)
                for admission in admissions:
                    admission.is_active = True
                    admission.save()
                # retrieve related FeeRecords
                fee_records = FeeRecord.objects.all_including_inactive().filter(student=student)
                for fee_record in fee_records:
                    fee_record.is_active = True
                    fee_record.save()
                # retrieve related Documents
                documents = Document.objects.all_including_inactive().filter(student=student)
                for document in documents:
                    document.is_active = True
                    document.save()
                # retrieve related Addresses
                addresses = Address.objects.all_including_inactive().filter(user=user)
                for address in addresses:
                    address.is_active = True
                    address.save()
                # retrieve Banking Details
                bank_details = BankingDetail.objects.all_including_inactive().filter(user=user)
                for bank_detail in bank_details:
                    bank_detail.is_active = True
                    bank_detail.save() 

                
                # Create Student.classes connection
                class_period_ids = request.data.get("class_period_ids", [])
                if class_period_ids:
                    valid_class_period = ClassPeriod.objects.filter(id__in=class_period_ids)
                    if valid_class_period:
                        student.classes.set(valid_class_period)
                    else:
                        return Response({"erorr": "Invalid class period ids"})
                    
                # Create StudentYearLevel connection 
                year_id = request.data.get("year_id")
                level_id = request.data.get("level_id")
                
                if year_id and level_id:
                    try:
                        level = YearLevel.objects.get(id=level_id)
                        year = SchoolYear.objects.get(id=year_id)
                        StudentYearLevel.objects.update_or_create(
                            student = student,
                            defaults={"year": year, "level": level}
                        )
                    except ObjectDoesNotExist:
                        return Response({"error":"Invalid year level id"})
                    
                # Create StudentGuardian connections
                guardian_ids = request.data.get("guardian_ids", [])
                if guardian_ids:
                    valid_guardians = Guardian.objects.filter(id__in=guardian_ids, is_active=True)
                    if valid_guardians.exists():
                        guardian_type_id = request.data.get("guardian_type_id")
                        try:
                            guardian_type = GuardianType.objects.get(id=guardian_type_id) if guardian_type_id else GuardianType.objects.get(name="Parent")
                            for guardian in valid_guardians:
                                StudentGuardian.objects.update_or_create(
                                    student=student,
                                    guardian=guardian,
                                    defaults={'guardian_type': guardian_type}
                                )
                        except ObjectDoesNotExist:
                            return Response({"error": "Invalid or inactive GuardianType ID provided"}, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        return Response({"error": "No valid or active Guardian IDs provided"}, status=status.HTTP_400_BAD_REQUEST)
                    

            # Handle Guardian   (Student guardian relation [make], address, docs)
            guardian = getattr(user, 'guardian_relation', None)
            if guardian is not None:
                guardian = user.guardian_relation
                guardian.is_active = True
                guardian.save()

                # update StudentGuardian connections
                student_ids = request.data.get("student_ids", [])
                if student_ids:
                    valid_students = Student.objects.filter(id__in=student_ids, is_active=True)
                    if valid_students.exists():
                        guardian_type_id = request.data.get("guardian_type_id")
                        try:
                            guardian_type = GuardianType.objects.get(id=guardian_type_id) if guardian_type_id else GuardianType.objects.get(name="Parent")  
                            for student in valid_students:
                                StudentGuardian.objects.update_or_create(
                                    student=student,
                                    guardian=guardian,
                                    defaults={'guardian_type': guardian_type}
                                )
                        except ObjectDoesNotExist:
                            return Response({"error": "Invalid or inactive GuardianType ID provided"})
                    else:
                        return Response({"error": "No valid or active Student IDs provided"})
                
                # retrieve related Addresses
                addresses = Address.objects.all_including_inactive().filter(user=user)
                for address in addresses:
                    address.is_active = True
                    address.save()
                # retrieve related Documents
                documents = Document.objects.all_including_inactive().filter(guardian=guardian)
                for document in documents:
                    document.is_active = True
                    document.save() 
                
            # Handle Teacher  (classPeriod [create {M2M}], teacheryearlevel, address, docs)
            teacher = getattr(user, 'teacher', None)
            if teacher is not None:
                teacher = user.teacher
                teacher.is_active = True
                teacher.save()

                # Assign teacher from ClassPeriod assignments
                class_period_ids = request.data.get("class_period_ids", [])
                if class_period_ids:
                    valid_class_periods = ClassPeriod.objects.filter(id__in=class_period_ids)
                    if valid_class_periods.exists():
                        for class_period in valid_class_periods:
                            class_period.teacher = teacher
                            class_period.save()
                    else:
                        return Response({"error": "No valid or active ClassPeriod IDs provided"})

                # Teacher year level reassigning
                year_level_id = request.data.get("year_level_id", [])
                if year_level_id:
                    valid_year_levels = YearLevel.objects.filter(id=year_level_id)
                    if valid_year_levels.exists():
                        teacher.year_levels.set(valid_year_levels)
                    else:
                        return Response({"error": "No valid or active YearLevel IDs provided"}, status=status.HTTP_400_BAD_REQUEST)

                # retrieve related Addresses
                addresses = Address.objects.all_including_inactive().filter(user=user)
                for address in addresses:
                    address.is_active = True
                    address.save()
                # retrieve related Documents
                documents = Document.objects.all_including_inactive().filter(teacher=teacher)
                for document in documents:
                    document.is_active = True
                    document.save()    
                    

            # Handle OfficeStaff  ([student,teacher,admisson {clear M2M}, address, docs])
            office_staff = getattr(user, 'office_staff', None)
            if office_staff is not None:
                office_staff = user.office_staff
                office_staff.is_active = True
                office_staff.save()

                # # Create ManyToMany relationships
                #  Student connection
                student_ids = request.data.get("student_ids", [])
                if student_ids:
                    valid_students = Student.objects.filter(id__in=student_ids, is_active=True)
                    if valid_students.exists():
                        office_staff.student.set(valid_students)
                    else:
                        return Response({"error": "No valid or active Student IDs provided"})

                # Teacher connection
                teacher_ids  = request.data.get("teacher_ids", [])
                if teacher_ids:
                    valid_teachers = Teacher.objects.filter(id__in=teacher_ids, is_active=True)
                    if valid_teachers.exists():
                        office_staff.teacher.set(valid_teachers)
                    else:
                        return Response({"error": "No valid or active Teacher IDs provided"})

                # Admission connection
                admission_ids = request.data.get("admission_ids", [])
                if admission_ids:
                    valid_admissions = Admission.objects.filter(id__in=admission_ids, is_active=True)
                    if valid_admissions.exists():
                        office_staff.admissions.set(valid_admissions)
                    else:
                        return Response({"error":"No valid or active Admission IDs provided"})
                    

                # retrieve related Addresses
                addresses = Address.objects.all_including_inactive().filter(user=user)
                for address in addresses:
                    address.is_active = True
                    address.save()
                # retrieve related Documents
                documents = Document.objects.all_including_inactive().filter(office_staff=office_staff)
                for document in documents:
                    document.is_active = True
                    document.save() 

            
            # Handle Director (if needed)
            director = getattr(user, 'director', None)
            if director is not None:
                director = user.director
                director.is_active = True
                director.save()
                # Deactivate related Addresses
                addresses = Address.objects.all_including_inactive().filter(user=user)
                for address in addresses:
                    address.is_active = True
                    address.save()

            # log termination
            UserStatusLog.objects.create(user=user, status='ACTIVATED', reason=user.deactivation_reason)
            serializer = UserSerializer(user)
            return Response({
                "message": f"User {user.id} has been successfully reactivated.",
                "user_id": user.id,
                "data": serializer.data})
    except User.DoesNotExist:
        return Response({"error": "User not found"})
    
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

        if "director" in role_names:
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
                return Response({"error": "You can only create papers for your assigned classes."}, status=403)
        
        else:
            return Response({"error": "You do not have permission to create exam papers."}, status=403)

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
        paper_code = request.data.get("paper_code")
        if not paper_code:
            return Response({"error": "paper_code is required for update."}, status=400)

        try:
            paper = ExamPaper.objects.get(paper_code=paper_code)
        except ExamPaper.DoesNotExist:
            return Response({"error": "ExamPaper not found"}, status=404)

        serializer = self.get_serializer(paper, data=request.data, partial=True)
        if serializer.is_valid():
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
                    "school_year": obj.term.year.year_name,
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



class StudentMarksView(viewsets.ModelViewSet):
    queryset = StudentMarks.objects.all()
    serializer_class = StudentMarksSerializer
    permission_classes = [IsAuthenticated,RoleBasedExamPermission] 
    api_section = "student_marks"  

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated], url_path="get_marks")
    def get_marks(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        if "director" in role_names:
            marks_qs = StudentMarks.objects.select_related(
                "student__student__user",
                "subject",
                "teacher__user",
                "exam_type",
                "term__year",
                "student__level"
            )
        elif "teacher" in role_names:
            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher not found."})

            assigned_class_ids = TeacherYearLevel.objects.filter(
                teacher=teacher
            ).values_list("year_level_id", flat=True)

            student_ids = StudentYearLevel.objects.filter(
                level_id__in=assigned_class_ids
            ).values_list("id", flat=True)

            marks_qs = StudentMarks.objects.select_related(
                "student__student__user",
                "subject",
                "teacher__user",
                "exam_type",
                "term__year",
                "student__level"
            ).filter(
                student_id__in=student_ids,
                teacher=teacher
            )
        else:
            return Response({"error": "You do not have permission to view marks."})

        # ----------- Filter
        school_year_filter = request.query_params.get("school_year")
        year_level_filter = request.query_params.get("year_level")
        exam_type_filter = request.query_params.get("exam_type")

        if school_year_filter:
            marks_qs = marks_qs.filter(term__year__year_name=school_year_filter)
        if year_level_filter:
            marks_qs = marks_qs.filter(student__level__level_name=year_level_filter)
        if exam_type_filter:
            marks_qs = marks_qs.filter(exam_type__name=exam_type_filter)

        if not marks_qs.exists():
            return Response({"message": "No data found."})

        grouped_data = {}
        for mark in marks_qs:
            teacher_name = mark.teacher.user.get_full_name().lower()
            subject_name = mark.subject.subject_name.lower()
            exam_type = mark.exam_type.name
            school_year = mark.term.year.year_name
            year_level = mark.student.level.level_name
            key = (teacher_name, subject_name, exam_type, school_year, year_level)

            grouped_data.setdefault(key, []).append({
                "name": mark.student.student.user.get_full_name().lower(),
                "marks": mark.marks_obtained
            })

        final_response = {}
        for (teacher_name, subject_name, exam_type, school_year, year_level), student_marks in grouped_data.items():
            group_key = (school_year, exam_type, year_level)
            final_response.setdefault(group_key, []).append({
                "teacher_name": teacher_name,
                "subject": subject_name,
                "student_marks": student_marks
            })

        formatted_output = {}
        for (school_year, exam_type, year_level), data in final_response.items():
            marks_filtered = marks_qs.filter(
                term__year__year_name=school_year,
                exam_type__name=exam_type,
                student__level__level_name=year_level
            )
            first_mark = marks_filtered.first()
            report_id = first_mark.id if first_mark else None
            report_key = f"id : {report_id}" if report_id else f"{school_year}_{exam_type}_{year_level}".replace(" ", "_").lower()

            formatted_output[report_key] = {
                "school_year": school_year,
                "exam_type": exam_type,
                "year_level": year_level,
                "data": data
            }

        return Response(formatted_output)



    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated], url_path='create_marks')
    def create_marks(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        is_director = "director" in role_names
        is_teacher = "teacher" in role_names

        if not (is_director or is_teacher):
            return Response({"error": "You do not have permission to perform this action."})

        if is_teacher:
            try:
                teacher = Teacher.objects.get(user=user)
            except Teacher.DoesNotExist:
                return Response({"error": "Teacher not found."})
            assigned_class_ids = TeacherYearLevel.objects.filter(
                teacher=teacher
            ).values_list("year_level_id", flat=True)
        else:
            teacher = None
            assigned_class_ids = []

        data = request.data
        school_year_id = data.get("school_year_id")
        exam_type_id = data.get("exam_type_id")
        year_level_id = data.get("year_level_id")

        # print("school_year_id:", school_year_id)
        # print("exam_type_id:", exam_type_id)
        # print("year_level_id:", year_level_id)

        if not school_year_id or not exam_type_id or not year_level_id:
            return Response({
                "error": "Missing required fields: school_year_id, exam_type_id, or year_level_id"
            }, status=400)

        try:
            school_year_obj = SchoolYear.objects.get(id=school_year_id)
            exam_type_obj = ExamType.objects.get(id=exam_type_id)
            year_level_obj = YearLevel.objects.get(id=year_level_id)
        except SchoolYear.DoesNotExist:
            return Response({"error": "Invalid school_year"})
        except ExamType.DoesNotExist:
            return Response({"error": "Invalid exam_type"})
        except YearLevel.DoesNotExist:
            return Response({"error": "Invalid year_level"})

        term_obj = Term.objects.filter(year=school_year_obj).first()
        if not term_obj:
            return Response({"error": "No term found for given school_year"})

        any_error = False
        errors = []     
        success = []   
        for group in data.get("data", []):
            teacher_id = group.get("teacher_id")
            subject_id = group.get("subject_id")

            try:
                teacher_obj = Teacher.objects.get(id=teacher_id)
                subject_obj = Subject.objects.get(id=subject_id)
            except (Teacher.DoesNotExist, Subject.DoesNotExist):
                any_error = True
                errors.append(f"Invalid teacher ({teacher_id}) or subject ({subject_id})")
                continue

            if is_teacher:
                if teacher.id != teacher_obj.id:
                    errors.append(f"Teacher mismatch: you are not allowed to submit for teacher ID {teacher_obj.id}")
                    any_error = True
                    continue
                if year_level_obj.id not in assigned_class_ids:
                    errors.append(f"Teacher not assigned to year_level ID {year_level_obj.id}")
                    any_error = True
                    continue

            for student_data in group.get("student_marks", []):
                student_id = student_data.get("student_id")
                marks = student_data.get("marks")

                try:
                    student_yl = StudentYearLevel.objects.get(id=student_id, level=year_level_obj)
                except StudentYearLevel.DoesNotExist:
                    errors.append(f"Student ID {student_id} not found in year_level {year_level_id}")
                    any_error = True
                    continue

                try:
                    obj, created = StudentMarks.objects.get_or_create(
                        student=student_yl,
                        exam_type=exam_type_obj,
                        term=term_obj,
                        subject=subject_obj,
                        teacher=teacher_obj,
                        defaults={"marks_obtained": marks}
                        
                    )
                    # print("Created:", created)
                    # print("Student:", student_id, "Subject:", subject_obj.subject_name, "Exists:", not created)

                    if created:
                        success.append(student_id)
                    else:
                        errors.append(f"Marks already exist for student {student_id} in subject {subject_obj.subject_name}")
                        any_error = True
                except Exception as e:
                    errors.append(f"Unexpected error for student {student_id}: {str(e)}")
                    any_error = True

        # print("Full request data:", data)
        # print("Errors encountered:", errors)

        if any_error:
            return Response({
                "message": "Some marks could not be inserted. Either already exist or invalid data.",
                "errors": errors
            }, status=400)

        return Response({
            "message": "Marks inserted successfully.",
            "inserted_student_ids": success
        }, status=201)




    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated], url_path='update_marks')
    def update_marks(self, request):
        user = request.user
        role_names = [role.name.lower() for role in user.role.all()]

        is_director = "director" in role_names
        is_teacher = "teacher" in role_names

        if not (is_director or is_teacher):
            return Response({"error": "You do not have permission to perform this action."}, status=403)

        data = request.data.get("data", [])
        school_year_id = request.data.get("school_year_id")
        exam_type_id = request.data.get("exam_type_id")
        year_level_id = request.data.get("year_level_id")

        errors = []
        updated_ids = []

        try:
            school_year = SchoolYear.objects.get(id=school_year_id)
            exam_type = ExamType.objects.get(id=exam_type_id)
            term = Term.objects.filter(year=school_year).first()

            if not term:
                return Response({"error": f"No term found for school year {school_year_id}"})

        except Exception as e:
            return Response({"error": str(e)}, status=400)

        for item in data:
            subject_id = item.get("subject_id")
            try:
                subject = Subject.objects.get(id=subject_id)
            except Subject.DoesNotExist:
                errors.append(f"Subject not found with id {subject_id}")
                continue

            for student_data in item.get("student_marks", []):
                student_id = student_data.get("student_id")
                marks = student_data.get("marks")

                try:
                    student = StudentYearLevel.objects.get(student__id=student_id, level_id=year_level_id)

                    student_mark = StudentMarks.objects.filter(
                        student=student,
                        subject=subject,
                        exam_type=exam_type,
                        term=term
                    ).first()

                    if not student_mark:
                        errors.append(f"Marks not found for student {student_id}, subject {subject_id}")
                        continue

                    student_mark.marks_obtained = marks
                    student_mark.save()
                    updated_ids.append(student_id)

                except StudentYearLevel.DoesNotExist:
                    errors.append(f"StudentYearLevel not found for student {student_id}")
                except Exception as e:
                    errors.append(f"Error updating student {student_id}: {str(e)}")

        if errors:
            return Response({
                "message": "Some marks could not be updated.",
                "errors": errors
            }, status=400)

        return Response({
            "message": "Marks updated successfully.",
            "updated": updated_ids
        },status=200)


"""-------------------------------------------RESULT---------------------------------------------------"""
from rest_framework.exceptions import PermissionDenied
from collections import defaultdict

class PersonalSocialQualityView(viewsets.ModelViewSet):
    queryset = PersonalSocialQuality.objects.all()
    serializer_class = PersonalSocialQualitySerializer
    # permission_classes = [IsAuthenticated,IsDirectororOfficeStaff]

class PersonalSocialGradeViewSet(viewsets.ModelViewSet):
    queryset = PersonalSocialQualityTermWise.objects.all()
    serializer_class = PersonalSocialGradeSerializer
    permission_classes = [IsAuthenticated]

    def _save_grade(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def _can_teacher_access_report_card(self, teacher, report_card_id):
        if not teacher.year_levels.exists():
            raise PermissionDenied("You are not assigned to any classes.")
        return ReportCard.objects.filter(
            id=report_card_id,
            student_level__level__in=teacher.year_levels.all()
        ).exists()

    def get_queryset(self):
        user = self.request.user
        roles = [role.name for role in user.role.all()]
        student_id = self.request.query_params.get("student_id")

        qs = PersonalSocialQualityTermWise.objects.all()

        if "office_staff" in roles or "director" in roles:
            if student_id:
                qs = qs.filter(report_card__student_level__student__id=student_id)
            return qs

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            if not teacher:
                return PersonalSocialQualityTermWise.objects.none()

            if not teacher.year_levels.exists():
                raise PermissionDenied("You are not assigned to any classes.")

            qs = qs.filter(
                report_card__student_level__level__in=teacher.year_levels.all()
            )

            if student_id:
                qs = qs.filter(report_card__student_level__student__id=student_id)

            return qs

        return PersonalSocialQualityTermWise.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        roles = [role.name for role in user.role.all()]

        if "office_staff" in roles or "director" in roles:
            return self._save_grade(request)

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            report_card_id = request.data.get("report_card")

            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)
            if not report_card_id:
                return Response({"error": "report_card ID is required"}, status=400)

            if self._can_teacher_access_report_card(teacher, report_card_id):
                return self._save_grade(request)
            else:
                return Response(
                    {"error": "You're not authorized to add grades for this report card."},
                    status=403
                )

        return Response({"error": "Not allowed for your role."}, status=403)

    def update(self, request, *args, **kwargs):
        user = request.user
        roles = [role.name for role in user.role.all()]
        instance = self.get_object()

        if "office_staff" in roles or "director" in roles:
            return super().update(request, *args, **kwargs)

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)

            report_card = instance.report_card
            if report_card.student_level.level in teacher.year_levels.all():
                return super().update(request, *args, **kwargs)
            else:
                return Response(
                    {"error": "Not authorized to update this grade."}, status=403
                )

        return Response({"error": "Not allowed for your role."}, status=403)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        roles = [role.name for role in user.role.all()]
        instance = self.get_object()

        if "office_staff" in roles or "director" in roles:
            return super().destroy(request, *args, **kwargs)

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)

            report_card = instance.report_card
            if report_card.student_level.level in teacher.year_levels.all():
                return super().destroy(request, *args, **kwargs)
            else:
                return Response(
                    {"error": "Not authorized to delete this grade."}, status=403
                )

        return Response({"error": "Not allowed for your role."}, status=403)

class NonScholasticGradeViewSet(viewsets.ModelViewSet):
    queryset = NonScholasticGradeTermWise.objects.all()
    serializer_class = NonScholasticGradeTermWiseSerializer
    permission_classes = [IsAuthenticated]

    def _save_grade(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def _can_teacher_access_report_card(self, teacher, report_card_id):
        return ReportCard.objects.filter(
            id=report_card_id,
            student_level__level__in=teacher.year_levels.all()
        ).exists()
    
    def get_queryset(self):
        user = self.request.user
        roles = [role.name for role in user.role.all()]
        # print("role:",roles)
        student_id = self.request.query_params.get("student_id")

        if "office_staff" in roles or "director" in roles:
            qs = NonScholasticGradeTermWise.objects.all()
            if student_id:
                qs = qs.filter(report_card__student_level__student__id=student_id)
            return qs

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            if not teacher:
                return PersonalSocialQualityTermWise.objects.none()

            if not teacher.year_levels.exists():
                raise PermissionDenied("You are not assigned to any classes.")

            qs = qs.filter(
                report_card__student_level__level__in=teacher.year_levels.all()
            )

            if student_id:
                qs = qs.filter(report_card__student_level__student__id=student_id)

            return qs


        return NonScholasticGradeTermWise.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        roles = [role.name for role in user.role.all()]

        if "office_staff" in roles or "director" in roles:
            return self._save_grade(request)

        elif "teacher" in roles:
            teacher = getattr(user, "teacher", None)
            report_card_id = request.data.get("report_card")

            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)
            if not report_card_id:
                return Response({"error": "report_card ID is required"}, status=400)

            if self._can_teacher_access_report_card(teacher, report_card_id):
                return self._save_grade(request)
            else:
                return Response({"error": "You're not authorized to add grades for this report card."}, status=403)

        return Response({"error": "Not allowed for your role."}, status=403)

    def update(self, request, *args, **kwargs):
        user = request.user
        roles =[role.name for role in user.role.all()]

        instance = self.get_object()

        if "office_staff" in roles or "director" in roles:
            return super().update(request, *args, **kwargs)

        elif "teacher" in roles:
            teacher = user.teacher
            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)

            report_card = instance.report_card
            if report_card.student_level.level in teacher.year_levels.all():
                return super().update(request, *args, **kwargs)
            else:
                return Response({"error": "Not authorized to update this grade."}, status=403)

        return Response({"error": "Not allowed for your role."}, status=403)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        roles = [role.name for role in user.role.all()]

        instance = self.get_object()

        if "office_staff" in roles or "director" in roles:
            return super().destroy(request, *args, **kwargs)

        elif "teacher" in roles:
            teacher = user.teacher
            if not teacher:
                return Response({"error": "Teacher profile not found."}, status=400)

            report_card = instance.report_card
            if report_card.student_level.level in teacher.year_levels.all():
                return super().destroy(request, *args, **kwargs)
            else:
                return Response({"error": "Not authorized to delete this grade."}, status=403)

        return Response({"error": "Not allowed for your role."}, status=403)
from director.permission import RoleBasedPermission

class ReportCardViewSet(viewsets.ModelViewSet):
    queryset = ReportCard.objects.all()
    serializer_class = ReportCardSerializer
    permission_classes = [IsAuthenticated, RoleBasedPermission]
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    def get_user_roles(self):
        user = self.request.user
        return [role.name for role in user.role.all()]

    def get_queryset(self):
        user = self.request.user
        roles = self.get_user_roles()

        student_id = self.request.query_params.get('student_id')
        standard_filter = self.request.query_params.get('standard')
        division_filter = self.request.query_params.get('division')

        if student_id:
            return self.queryset.filter(student_level__student__id=student_id)

        if standard_filter:
            return self.queryset.filter(student_level__level__level_name=standard_filter)
        
        if division_filter:
            return self.queryset.filter(report_card__division=division_filter)


        if 'director' in roles or 'office staff' in roles:
            return self.queryset

        if 'teacher' in roles:
            try:
                teacher = user.teacher
                return self.queryset.filter(
                    student_level__level__in=teacher.year_levels.all()
                )
            except Teacher.DoesNotExist:
                return self.queryset.none()

        if 'guardian' in roles:
            student_ids = StudentGuardian.objects.filter(
                guardian__user=user
            ).values_list('student_id', flat=True)
            return self.queryset.filter(student_level__student__id__in=student_ids)

        if 'student' in roles:
            return self.queryset.filter(student_level__student__user=user)

        return self.queryset.none()


    def get_attendance_string(self, report_card):
        student_level = report_card.student_level
        attendance_qs = StudentAttendance.objects.filter(student=student_level.student)
        present = attendance_qs.filter(status='P').count()
        total = 230
        attendance= f"{present}/{total}" 
        return attendance

    def get_promoted_class(self, report_card):
        # division = report_card.division
        sup = report_card.supplementary_in
        failed_subjects = [s.strip() for s in ( sup or "").split(",") if s.strip()]
        
        if failed_subjects:
            return None
        
        # if division=="Fail":
        #     return None
            
        current_level = report_card.student_level.level
        current_year = report_card.student_level.year
        student = report_card.student_level.student

        # Try getting the next level
        next_level = YearLevel.objects.filter(level_order=current_level.level_order + 1).first()
        if not next_level:

            return None  # Already in the highest class
        
        next_year = SchoolYear.objects.filter(start_date__gt=current_year.start_date).order_by('start_date').first()
        if not current_year or not current_year.start_date:
            return None

        
        # Get or create the corresponding StudentYearLevel for next class in same year
        promoted_to, _ = StudentYearLevel.objects.get_or_create(
            student=student,
            level=next_level,
            year=next_year # or next academic year if needed
        )
        return promoted_to 

    def get_document(self, report_card):
        documents_data = []

        for doc_rel in report_card.documents.select_related("documents").all():
            document = doc_rel.documents
            if document:
                doc_types = list(document.document_types.values_list("name", flat=True))
                documents_data.append({
                    "identities": document.identities,
                    "document_types": doc_types
                })

        return documents_data

    def get_non_scholastic_data(self,report_card):
        return [
            {
                "subject": item.non_scholastic_subject.subject_name,
                "term": f"Term {item.term.term_number}",
                "grade": item.grade
            }
            for item in report_card.non_scholastic_grades.select_related("term", "non_scholastic_subject")
        ]
        
    def get_subject_score(self, report_card):
        from collections import defaultdict

        temp = defaultdict(dict)

        for score in report_card.subject_scores.select_related(
            "marks_obtained__student",
            "marks_obtained__subject",
            "marks_obtained__exam_type"
        ).all():
            mark = score.marks_obtained
            if mark and mark.subject and mark.exam_type:
                exam_type = mark.exam_type.name.lower()  # normalize to lowercase
                subject = mark.subject.subject_name
                temp[exam_type][subject] = float(mark.marks_obtained or 0)

        examwise_subjects = []
        for exam_type, subjects in temp.items():
            subject_count = len(subjects)
            is_fa = exam_type.startswith("fa")  # check if it's FA
            max_per_subject = 10 if is_fa else 100  # apply correct max marks
            total = sum(subjects.values())
            max_marks = subject_count * max_per_subject
            percentage = round((total / max_marks) * 100, 2) if max_marks else 0

            #  Add grading logic
            if percentage >= 90:
                grade = "A+"
            elif percentage >= 75:
                grade = "A"
            elif percentage >= 60:
                grade = "B"
            elif percentage >= 50:
                grade = "C"
            elif percentage >= 40:
                grade = "D"
            else:
                grade = "F"

            #  Append full exam summary
            examwise_subjects.append({
                "exam_type": exam_type,
                "subjects": subjects,
                "total": total,
                "max_marks": max_marks,
                "percentage": percentage,
                "grade": grade
            })

        return examwise_subjects

    def sync_subject_scores(self, report_card):
        terms = Term.objects.filter(year=report_card.student_level.year)

        student_marks = StudentMarks.objects.filter(
            student=report_card.student_level,
            term__in=terms
        )
        for mark in student_marks:
            SubjectScore.objects.get_or_create(report_card=report_card, marks_obtained=mark)
    
    def save_documents(self, report_card):
        student = report_card.student_level.student
        student_docs = Document.objects.filter(
            student=student,
            document_types__isnull=False
        ).distinct()

        for doc in student_docs:
            # Only link if not already linked
            if not ReportCardDocument.objects.filter(report_card=report_card, documents=doc).exists():
                ReportCardDocument.objects.create(report_card=report_card, documents=doc)

    def save_subject_scores(self, report_card, subjects_data):
        for subject_data in subjects_data:
            subject_name = subject_data.get("subject")
            if not subject_name:
                continue
            subject = Subject.objects.get(subject_name=subject_name)
            for exam_key in ["fa1", "fa2", "fa3", "sa1", "sa2", "sa3"]:
                marks = subject_data.get(exam_key)
                if marks is not None:
                    exam_type = ExamType.objects.get(name__iexact=exam_key.upper())
                    term = Term.objects.filter(year=report_card.student_level.year.year_name).first()
                    student_marks = StudentMarks.objects.create(
                        exam_type=exam_type,
                        subject=subject,
                        term=term,
                        student=report_card.student_level.student,
                        teacher=Teacher.objects.first(),
                        marks_obtained=marks
                    )
                    SubjectScore.objects.create(
                        report_card=report_card,
                        marks_obtained=student_marks
                    )
                    # print("RC ID", report_card.id)  

    def save_non_scholastic(self, report_card, grades):
        for subject_name, values in grades.items():
            subject = Subject.objects.get(subject_name=subject_name)
            for term_key, grade in values.items():
                term = Term.objects.get(name__iexact=term_key)
                NonScholasticGradeTermWise.objects.create(
                    report_card=report_card,
                    non_scholastic_subject=subject,
                    term=term,
                    grade=grade
                )

    def save_personal_social(self, report_card, data):
        all_qualities = PersonalSocialQuality.objects.all()
        for term_key, quality_dict in data.items():
            term_number = 1 if term_key == "Term 1" else 2
            term = Term.objects.get(term_number=term_number, year=report_card.student_level.year)
            for quality in all_qualities:
                grade = quality_dict.get(quality.quality_name)
                if grade:
                    NonScholasticGradeTermWise.objects.create(
                        report_card=report_card,
                        personal_quality=quality,
                        term=term,
                        grade=grade
                    )



    def create(self, request, *args, **kwargs):
        roles = self.get_user_roles()
        if 'director' not in roles:
            if 'teacher' in roles:
                teacher = getattr(request.user, 'teacher', None)
                student_level_id = request.data.get("student_level")
                if teacher and student_level_id:
                    try:
                        student_level = StudentYearLevel.objects.get(id=student_level_id)
                        if student_level.level not in teacher.year_levels.all():
                            return Response({"error": "Permission denied."}, status=403)
                    except StudentYearLevel.DoesNotExist:
                        return Response({"error": "Invalid student_level ID."}, status=400)
                else:
                    return Response({"error": "Permission denied."}, status=403)
            else:
                return Response({"error": "Permission denied."}, status=403)
            
        data = request.data.copy()
        student_level = StudentYearLevel.objects.get(id=data.get("student_level"))
        student = student_level.student
        academic_year = student_level.year
        student_level = StudentYearLevel.objects.get(student=student, year=academic_year)

        existing = ReportCard.objects.filter(student_level=student_level).first()
        if existing:
            return Response(
                {"error": "Report card for this student and academic year already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # STEP 1: Create report_card first with temporary placeholder values
        report_card = ReportCard.objects.create(
            student_level=student_level,
            total_marks=0,
            max_marks=0,
            percentage=0.0,
            grade="F",
            division="Fail",
            rank=data.get("rank"),
            attendance=None,
            supplementary_in = [],
            teacher_remark=data.get("teacher_remark"),
            promoted_to_class= None,#self.get_promoted_class(ReportCard),  
            school_reopen_date=parse_date(data.get("school_reopen_date"))
        )

        # STEP 2: Save related data (required for subject score calc)
        self.save_documents(report_card)
        self.save_subject_scores(report_card, data.get("subjects", []))
        self.save_non_scholastic(report_card, data.get("non_scholastic", {}))
        self.save_personal_social(report_card, data.get("personal_social", {}))

        # STEP 3: Sync marks to SubjectScore and recalculate
        self.sync_subject_scores(report_card)
        subjects = self.get_subject_score(report_card)
        subject_avg = calculate_subject_summary(subjects)

        total_obtained = subject_avg["total_marks"]
        total_possible = subject_avg["max_marks"]
        percentage = subject_avg["percentage"]
        grade = subject_avg["grade"]
        supplementary_in = ", ".join(subject_avg["supplementary_in"]) if subject_avg["supplementary_in"] else ""

        if percentage >= 60:
            division = "First"
        elif percentage >= 50:
            division = "Second"
        elif percentage >= 40:
            division = "Third"
        else:
            division = "Fail"

        # STEP 4: Save final calculated fields
        report_card.attendance = self.get_attendance_string(report_card)
        report_card.total_marks = total_obtained
        report_card.max_marks = total_possible
        report_card.percentage = percentage
        report_card.grade = grade
        report_card.division = division
        report_card.supplementary_in = supplementary_in
        report_card.promoted_to_class = self.get_promoted_class(report_card)
        
        report_card.save()

        return Response(self.build_report_card_response(report_card), status=status.HTTP_201_CREATED)
    
    def build_report_card_response(self, report_card):
        student = report_card.student_level.student
        user = student.user
        
        self.sync_subject_scores(report_card)
        subjects = self.get_subject_score(report_card)

        subject_avg = calculate_subject_summary(subjects)

        total_obtained = subject_avg["total_marks"]
        total_possible = subject_avg["max_marks"]
        percentage = subject_avg["percentage"]
        grade = subject_avg["grade"]
        supplementary_in = subject_avg["supplementary_in"]

        if percentage >= 60:
            division = "First"
        elif percentage >= 50:
            division = "Second"
        elif percentage >= 40:
            division = "Third"
        else:
            division = "Fail"


        documents_list = []

        for doc_link in report_card.documents.select_related("documents").all():
            doc = doc_link.documents
            if doc and doc.document_types.exists():
                try:
                    # Force identities into list if stored as a string
                    identities = doc.identities
                    if isinstance(identities, str):
                        identities = json.loads(identities)

                    if not isinstance(identities, list):
                        identities = [identities]

                    for doc_type in doc.document_types.all():
                        documents_list.append({doc_type.name: identities[0] if identities else None})

                except Exception as e:
                    # fallback when json.loads fails
                    print("Error parsing identities:", e)
                    continue

                    
        non_scholastic = {}
        for ns_grade in report_card.non_scholastic_grades.select_related("non_scholastic_subject", "term"):
            subject = ns_grade.non_scholastic_subject.subject_name
            term = f"Term {ns_grade.term.term_number}"
            if subject not in non_scholastic:
                non_scholastic[subject] = {}
            non_scholastic[subject][term] = ns_grade.grade

        personal_social = [
            {
                "quality": psq.personal_quality.quality_name,
                "term": f"Term {psq.term.term_number}",
                "grade": psq.grade
            }
            for psq in report_card.personal_qualities.select_related("personal_quality", "term")
        ]

        full_name = " ".join(filter(None, [user.first_name, user.middle_name, user.last_name]))

        return {
            "id": report_card.id,
            "student": student.id,
            "student_name": full_name,
            "father_name": student.father_name,
            "mother_name": student.mother_name,
            "date_of_birth": student.date_of_birth,
            "contact_number": student.contact_number,
            "scholar_number": student.scholar_number,
            "standard": report_card.student_level.level.level_name,
            "academic_year": report_card.student_level.year.year_name,
            "total_marks": total_obtained,
            "max_marks": total_possible,
            "percentage": percentage,
            "grade": grade,
            "division": division,
            "rank": report_card.rank,
            "attendance": self.get_attendance_string(report_card),
            "teacher_remark": report_card.teacher_remark,
            "supplementary_in": supplementary_in,
            "promoted_to_class": (report_card.promoted_to_class.level.level_name 
                if report_card.promoted_to_class and report_card.promoted_to_class.level 
                else None),
            "school_reopen_date": report_card.school_reopen_date,
            "documents": documents_list,
            "subjects": self.get_subject_score(report_card),
            "subject_avg": subject_avg["subject_avg"],
            "non_scholastic": self.get_non_scholastic_data(report_card),
            "personal_social": personal_social,

        } 

    def retrieve(self, request, *args, **kwargs):
        report_card = self.get_object()
        data = self.build_report_card_response(report_card)
        return Response(data)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response([self.build_report_card_response(rc) for rc in queryset])

    def update(self, request, *args, **kwargs):
        roles = self.get_user_roles()
        if 'director' not in roles:
            if 'teacher' in roles:
                teacher = getattr(request.user, 'teacher', None)
                instance = self.get_object()
                if not teacher or instance.student_level.level not in teacher.year_levels.all():
                    return Response({"error": "Permission denied."}, status=403)
            else:
                return Response({"error": "Permission denied."}, status=403)
            
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        data = request.data

        instance.total_marks = data.get("total_marks", instance.total_marks)
        instance.max_marks = data.get("max_marks", instance.max_marks)
        instance.percentage = data.get("percentage", instance.percentage)
        instance.grade = data.get("grade", instance.grade)
        instance.division = data.get("division", instance.division)
        instance.rank = data.get("rank", instance.rank)
        instance.attendance = data.get("attendance", instance.attendance)
        instance.teacher_remark = data.get("teacher_remark", instance.teacher_remark)
        instance.supplementary_in = data.get("supplementary_in", instance.supplementary_in)
        instance.school_reopen_date = data.get("school_reopen_date", instance.school_reopen_date)

        promoted_id = data.get("promoted_to_class")
        if promoted_id:
            instance.promoted_to_class_id = promoted_id

        instance.save()

        subjects_data = data.get("subjects", [])
        if subjects_data:
            instance.subject_scores.all().delete()
            for sub in subjects_data:
                subject_name = sub.get("subject")
                exam_type = sub.get("exam_type")
                marks = sub.get("marks")
                try:
                    subject_obj = Subject.objects.get(subject_name=subject_name)
                    exam_type_obj = ExamType.objects.get(name=exam_type)
                    student_mark = StudentMarks.objects.create(
                        student=instance.student,
                        subject=subject_obj,
                        exam_type=exam_type_obj,
                        marks_obtained=marks,
                        term=Term.objects.filter(year=instance.academic_year.year).first()
                    )
                    SubjectScore.objects.create(report_card=instance, marks_obtained=student_mark)
                except Exception as e:
                    print("Subject Update Error:", e)


        documents_data = data.get("documents", {})
        if documents_data:
            # Clear existing linked documents
            instance.documents.all().delete()

            #  Fetch all documents related to the same student
            student_docs = Document.objects.filter(student=instance.student_level.student)

            #  Link all of them to the report card
            for doc in student_docs:
                ReportCardDocument.objects.create(
                    report_card=instance,
                    documents=doc
                )


        non_scholastic_data = data.get("non_scholastic", {})
        if non_scholastic_data:
            instance.non_scholastic_grades.all().delete()
            for subject_name, terms in non_scholastic_data.items():
                subject_obj = Subject.objects.get(subject_name=subject_name)
                for term_name, grade in terms.items():
                    term_obj = Term.objects.get(term_number=term_name)
                    NonScholasticGradeTermWise.objects.create(
                        report_card=instance,
                        non_scholastic_subject=subject_obj,
                        term=term_obj,
                        grade=grade
                    )

        personal_data = data.get("personal_social", [])
        if personal_data:
            instance.personal_qualities.all().delete()
            for item in personal_data:
                quality = item.get("quality")
                term = item.get("term")
                grade = item.get("grade")
                try:
                    quality_obj = PersonalSocialQuality.objects.get(quality_name=quality)
                    term_obj = Term.objects.get(term_number=term)
                    PersonalSocialQualityTermWise.objects.create(
                        report_card=instance,
                        personal_quality=quality_obj,
                        term=term_obj,
                        grade=grade
                    )
                except Exception as e:
                    print("PSQ Update Error:", e)

        return self.retrieve(request, *args, **kwargs)



# ---------------------Expense 

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
    queryset = SchoolExpense.objects.all()
    serializer_class = SchoolExpenseSerializer
    # permission_classes = [IsAuthenticated, ExpensePermission]

    # def get_queryset(self):
    #     current_year = get_current_school_year()
    #     if current_year:
    #         return SchoolExpense.objects.filter(school_year=current_year)
    #     return SchoolExpense.objects.none()

    def get_queryset(self):
        queryset = SchoolExpense.objects.all()

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(category__name__icontains=search) |
                Q(description__icontains=search) |
                Q(payment_method__icontains=search) |
                Q(status__icontains=search) |
                Q(created_by__first_name__icontains=search) |
                Q(created_by__last_name__icontains=search) |
                Q(expense_date__icontains=search)
            )


        school_year_id = self.request.query_params.get("school_year")
        if school_year_id:
            queryset = queryset.filter(school_year_id=school_year_id)
        else:
            current_year = get_current_school_year()
            if current_year:
                queryset = queryset.filter(school_year=current_year)

        category_id = self.request.query_params.get("category")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        month = self.request.query_params.get("month")
        if month:
            queryset = queryset.filter(expense_date__month=month)

        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset



    def list(self, request):
        current_year = get_current_school_year()
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

        # return Response({
        #     "school_year": current_year.year_name if current_year else None,
        #     "data": serializer.data
        # })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user

        payment_method = serializer.validated_data.get("payment_method")   # safe access
        amount = serializer.validated_data.get("amount")

        if not payment_method:
            return Response({"error": "payment_method is required"}, status=status.HTTP_400_BAD_REQUEST)

        expense = SchoolExpense.objects.create(
            category=serializer.validated_data["category"],
            school_year=serializer.validated_data["school_year"],
            amount=amount,
            description=serializer.validated_data.get("description"),
            expense_date=serializer.validated_data["expense_date"],
            payment_method=payment_method,
            created_by=user,
            attachment=serializer.validated_data.get("attachment")

        )

        if payment_method == "cash":
            expense.status = "approved"
            expense.approved_by = user
            expense.save()
            # return Response(SchoolExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
            return Response({"message": "Expense approved successfully","expense": SchoolExpenseSerializer(expense).data}, status=status.HTTP_201_CREATED)


        elif payment_method == "cheque":
            expense.status = "pending"  
            expense.save()
            # return Response(SchoolExpenseSerializer(expense).data, status=status.HTTP_201_CREATED)
            return Response({"message": "Expense created and pending approval","expense": SchoolExpenseSerializer(expense).data}, status=status.HTTP_201_CREATED)


        elif payment_method == "online":
            # Call initiate_expense_payment function
            # return self.initiate_expense_payment(request, expense=expense)
            return Response({"message": "Use initiate-expense-payment API for online payments."},
                        status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": "Invalid payment method"}, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=["post"], url_path="initiate-expense-payment")
    def initiate_expense_payment(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        expense = serializer.save(
            created_by=request.user,
            status="pending",
            payment_method="online"
        )

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(expense.amount * 100),
            "currency": "INR",
            "payment_capture": "1",
            "receipt": f"EXP-{expense.id}"
        })

        expense.razorpay_order_id = razorpay_order["id"]
        expense.save()

        return Response({
            "expense_id": expense.id,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "amount": str(expense.amount),
            "currency": "INR",
            "status": expense.status
        }, status=status.HTTP_201_CREATED)



    @action(detail=False, methods=["post"], url_path="confirm-expense-payment")
    def confirm_expense_payment(self, request):
        data = request.data
        required = ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature", "expense_id"]
        missing = [f for f in required if f not in data]
        if missing:
            return Response({"error": f"Missing fields: {', '.join(missing)}"}, status=400)

        try:
            expense = SchoolExpense.objects.get(id=data["expense_id"], razorpay_order_id=data["razorpay_order_id"])
        except SchoolExpense.DoesNotExist:
            return Response({"error": "Expense not found or order mismatch"}, status=404)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"],
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment verification failed."}, status=400)

        expense.status = "approved"
        expense.razorpay_payment_id = data["razorpay_payment_id"]
        expense.razorpay_signature = data["razorpay_signature"]
        expense.approved_by = request.user
        expense.save()

        return Response({
            "message": "Expense payment confirmed",
            "expense": SchoolExpenseSerializer(expense).data
        })


    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        roles = [role.name.lower() for role in request.user.role.all()]

        if "status" in serializer.validated_data:
            if "director" not in roles:
                return Response(
                    {"error": "Only Director can update expense status."},
                    status=status.HTTP_403_FORBIDDEN
                )

            instance.status = serializer.validated_data["status"]
            instance.approved_by = request.user
            serializer.validated_data.pop("status", None)


        # Update remaining fields
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return Response({
            "message": "Expense updated successfully",
            "data": self.get_serializer(instance).data
        })



    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Expense deleted successfully"},
            status=status.HTTP_200_OK
        )
    


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
        user_id = request.data.get("user")
        if not user_id:
            return Response({"error": "user is required."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid user id."}, status=400)

        roles = [r.name.lower() for r in user.role.all()]
        if not any(r in ["teacher", "office staff"] for r in roles):
            return Response(
                {"error": "Only Teacher or Office Staff can be assigned as employee."},
                status=400
            )

        if Employee.objects.filter(user=user).exists():
            return Response({"error": "Employee already exists."}, status=400)

        employee = Employee.objects.create(
            user=user,
            joining_date=request.data.get("joining_date"),
            base_salary=request.data.get("base_salary"),
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


    # @action(detail=False, methods=["delete"], url_path="delete_emp")
    # def delete_emp(self, request):
    #     try:
    #         employee = Employee.objects.get(id=request.data.get("id"))
    #         employee.delete()
    #         return Response({"message": "Employee deleted successfully."})
    #     except Employee.DoesNotExist:
    #         return Response({"error": "Employee not found"}, status=404)


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

        if hasattr(user, "employee"):
            queryset = queryset.filter(user=user.employee)

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


    #     salary = EmployeeSalary.objects.create(
    #         user=serializer.validated_data["user"],
    #         school_year=serializer.validated_data["school_year"],
    #         month=serializer.validated_data["month"],
    #         deductions=serializer.validated_data.get("deductions", 0),
    #         gross_amount=serializer.validated_data.get("gross_amount", 0),
    #         net_amount=serializer.validated_data.get("net_amount", 0),
    #         payment_date=serializer.validated_data["payment_date"],
    #         payment_method=payment_method,
    #         remarks=serializer.validated_data.get("remarks"),
    #     )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        # salary = serializer.save()   
        today = date.today()
        try:
            current_year = SchoolYear.objects.get(start_date__lte=today, end_date__gte=today)
        except SchoolYear.DoesNotExist:
            raise serializers.ValidationError({"school_year": "No active school year found."})

        user = serializer.validated_data["user"]
        month = serializer.validated_data["month"]

        # DB-level duplicate check
        if EmployeeSalary.objects.filter(user=user, month=month, school_year=current_year).exists():
            return Response(
                {"error": "Salary record for this employee, month and school year already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        salary = serializer.save(school_year=current_year)
        payment_method = salary.payment_method

        if payment_method == "cash":
            salary.status = "paid"
            salary.paid_by = request.user
            salary.save()
            return Response(EmployeeSalarySerializer(salary).data, status=status.HTTP_201_CREATED)
        
        elif payment_method == "cheque":
            salary.status = "pending"
            salary.save()
            return Response(EmployeeSalarySerializer(salary).data, status=status.HTTP_201_CREATED)

        elif payment_method == "online":
            return Response(
                {"message": "Use initiate-salary-payment API for online payments."},
                status=status.HTTP_400_BAD_REQUEST
            )
        else:
            return Response({"error": "Invalid payment method"}, status=status.HTTP_400_BAD_REQUEST)

        # return Response(EmployeeSalarySerializer(salary).data, status=status.HTTP_201_CREATED)
        
        return Response({
            "message": "Salary record created successfully",
            "data": EmployeeSalarySerializer(salary).data
        }, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=["post"], url_path="initiate-salary-payment")
    def initiate_salary_payment(self, request):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        salary = serializer.save(
            status="pending",
            payment_method="online"
        )
        if salary.net_amount <= 0:
            return Response(
                {"error": "Net amount must be greater than 0 for online payment."},
                status=status.HTTP_400_BAD_REQUEST
            )

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            "amount": int(salary.net_amount * 100),
            "currency": "INR",
            "payment_capture": "1",
            "receipt": f"EMP-SAL-{salary.id}"
        })

        salary.razorpay_order_id = razorpay_order["id"]
        salary.save()

        return Response({
            "salary_id": salary.id,
            "razorpay_order_id": razorpay_order["id"],
            "razorpay_key": settings.RAZORPAY_KEY_ID,
            "net_amount": str(salary.net_amount),
            "currency": "INR",
            "status": salary.status
        }, status=status.HTTP_201_CREATED)


    @action(detail=False, methods=["post"], url_path="confirm-salary-payment")
    def confirm_salary_payment(self, request):
        data = request.data
        required_fields = ["razorpay_payment_id", "razorpay_order_id", "razorpay_signature", "salary_id"]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return Response({"error": f"Missing required fields: {', '.join(missing)}"}, status=400)

        try:
            salary = EmployeeSalary.objects.get(id=data["salary_id"], razorpay_order_id=data["razorpay_order_id"])
        except EmployeeSalary.DoesNotExist:
            return Response({"error": "Salary record not found or order mismatch"}, status=404)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": data["razorpay_order_id"],
                "razorpay_payment_id": data["razorpay_payment_id"],
                "razorpay_signature": data["razorpay_signature"]
            })
        except razorpay.errors.SignatureVerificationError:
            return Response({"error": "Payment verification failed."}, status=400)

        salary.status = "paid"
        salary.paid_by = request.user
        salary.razorpay_payment_id = data["razorpay_payment_id"]
        salary.razorpay_order_id = data["razorpay_order_id"]   
        salary.razorpay_signature = data["razorpay_signature"]
        salary.save()

        return Response({
            "message": "Salary payment confirmed",
            "salary": EmployeeSalarySerializer(salary).data
        })



    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        roles = [role.name.lower() for role in request.user.role.all()]

        if "status" in serializer.validated_data:
            if "director" not in roles:
                return Response({"error": "Only Director can update salary status."}, status=status.HTTP_403_FORBIDDEN)

            instance.status = serializer.validated_data["status"]
            instance.paid_by = request.user
            serializer.validated_data.pop("status", None)

        # Update remaining fields
        for attr, value in serializer.validated_data.items():
            setattr(instance, attr, value)
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
        # calculate totals
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


