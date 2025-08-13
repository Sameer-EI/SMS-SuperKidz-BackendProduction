from django.forms import DateField
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Count
from collections import OrderedDict
from .serializers import *
from rest_framework import filters
from .models import *
from rest_framework .views import APIView       # As of 07May25 at 12:30 PM
# from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Sum
from rest_framework.decorators import action

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
import json  # 🔸 This goes at the top of the file
from django.db.models import Q
from collections import OrderedDict, defaultdict
from datetime import datetime, timedelta
from django.utils.timezone import now
from django.db.models.functions import Cast



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
        user = User.objects.get(id=id)
        teacher = user.teacher
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)
    except Teacher.DoesNotExist:
        return Response({"error": "This user is not a teacher"}, status=400)

    periods = ClassPeriod.objects.filter(teacher=teacher)
    class_data = []
    seen = set()

    for period in periods:
        students = Student.objects.filter(classes=period).distinct()

        # ✅ FIXED: Use correct reverse relation from YearLevel
        year_levels = YearLevel.objects.filter(
            studentyearlevel__student__in=students
        ).distinct()

        for level in year_levels:
            key = (level.id, period.id)
            if key not in seen:
                seen.add(key)

                student_count = Student.objects.filter(
                    student_year_levels__level=level,
                    classes=period
                ).distinct().count()

                class_data.append({
                    "level_name": level.level_name,
                    "student_count": student_count,
                    "class_period": period.name,
                    "subject": period.subject.subject_name,
                    "classroom": period.classroom.room_name,
                })

    return Response({
        "teacher": f"{teacher.user.first_name} {teacher.user.last_name}",
        "total_classes": periods.count(),
        "class_details": class_data
    })


#   -------------------------------------------  Guardian Dashboard  ----------------------------------------------------------


@api_view(["GET"])
def guardian_dashboard(request, id=None):
    if not id:
        return Response({"error": "Guardian ID is required"}, status=400)

    try:
        guardian = Guardian.objects.get(user__id=id)  # Corrected line
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


@api_view(["GET"])
def student_dashboard(request, id=None):
    if not id:
        return Response({"error": "Student ID is required"}, status=400)

    try:
        student = Student.objects.get(user__id=id)
    except Student.DoesNotExist:
        return Response({"error": "Student not found"}, status=404)

    year_level_info = StudentYearLevel.objects.filter(student=student).last()

    guardian_links = StudentGuardian.objects.filter(student=student)
    guardians_data = []

    for link in guardian_links:
        guardian = link.guardian
        guardians_data.append({
            "guardian_name": f"{guardian.user.first_name} {guardian.user.last_name}"
        })

    return Response({
        "guardian": guardians_data, 
        "total_children": 1,
        "children": [{
            "student_name": f"{student.user.first_name} {student.user.last_name}",
            "class": f"{year_level_info.level.level_name} ({year_level_info.year.year_name})"
            if year_level_info else "Not Assigned"
        }]
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
    
    
class ClassPeriodView(viewsets.ModelViewSet):
    queryset = ClassPeriod.objects.all()
    serializer_class = ClassPeriodSerializer    


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


class AdmissionView(viewsets.ModelViewSet):
    queryset = Admission.objects.all()
    serializer_class = AdmissionSerializer
    # parser_classes=[MultiPartParser,FormParser]
    
    # ***************OfficeStaffView**************
    
class OfficeStaffView(viewsets.ModelViewSet):
    queryset=OfficeStaff.objects.all()
    serializer_class = OfficeStaffSerializer  
    
    
    def get_permissions(self):
        # Public access to list and retrieve
        if self.action in ['list', 'retrieve', 'update', 'partial_update']:
            return [AllowAny()]
        return [IsAuthenticated()]

    # ******************JWT***************
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





class DocumentView(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser)

    def create(self, request, *args, **kwargs):
        files = request.FILES.getlist('uploaded_files')
        document_types = request.data.getlist('document_types')
        identities = request.data.getlist('identities')

        if not files:
            return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        if not document_types:
            return Response({"error": "At least one document type must be selected."}, status=status.HTTP_400_BAD_REQUEST)
        if not identities:
            return Response({"error": "Identities are required."}, status=status.HTTP_400_BAD_REQUEST)

        if len(document_types) != len(identities):
            return Response({"error": "Identities count must match document types count."}, status=status.HTTP_400_BAD_REQUEST)

        data = request.data.copy()
        data.setlist('uploaded_files', files)
        data.setlist('document_types', document_types)
        data.setlist('identities', identities)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)






    

    
    
    
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

    def get_queryset(self):           # just commneted as of 27june25 at 02:47 PM
        return YearLevelFee.objects.select_related('year_level', 'fee_type')
    
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
        '+918847418400',
        '+918102637122'
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

# Fee Record View
# https://187gwsw1-8000.inc1.devtunnels.ms/d/fee-record/
class FeeRecordView(viewsets.ModelViewSet):
    serializer_class = FeeRecordSerializer
    queryset = FeeRecord.objects.all()
    filter_backends = [SearchFilter]

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
        queryset = super().get_queryset()
        request = self.request

        year_level_id = request.query_params.get('year_level')
        if year_level_id:
            queryset = queryset.filter(year_level_fees__year_level__id=year_level_id)

        search = request.query_params.get('search')
        if search:
            search = search.strip()
            search_parts = search.split(" ")

            if len(search_parts) > 1:
                queryset = queryset.filter(
                    Q(student__user__first_name__icontains=search_parts[0]) &
                    Q(student__user__last_name__icontains=' '.join(search_parts[1:]))
                )
            else:
                queryset = queryset.filter(
                    Q(student__user__first_name__icontains=search) |
                    Q(student__user__last_name__icontains=search)
                )

        return queryset.distinct()

    
    @action(detail=False, methods=['post'], url_path='submit_single_multi_month_fees')
    def submit_single_multi_month_fees(self, request):
        student_id = request.data.get('student_id')
        months = request.data.get('months', [])
        year_level_fees = request.data.get('year_level_fees', [])
        paid_amount = Decimal(request.data.get('paid_amount', "0.00"))
        payment_mode = request.data.get('payment_mode')
        remarks = request.data.get('remarks')
        received_by = request.data.get('received_by')

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
            full_data = FeeRecordSerializer(instance).data

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
            total = item["total_amount"] + item["late_fee"]
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

        qs = self.get_queryset()
        filters = Q()

        if month:
            filters &= Q(month__iexact=month)


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

        formatted_summary = []
        for item in summary:
            total = item["total_amount"] + item["late_fee"]
            due = max(0, total - item["paid_amount"])

            formatted_summary.append({
                "month": item["month"],
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