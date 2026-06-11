

# ***********************************2222**************************


# from django.db import models
# import os
# def Document_folder(instance, filename):
#     base_path = "Document_folder"

#     if instance.document and instance.document.student:
#         user = instance.document.student.user
#         year_level = (
#             instance.document.student.studentyearlevel_set.first().level.level_name
#             if instance.document.student.studentyearlevel_set.exists()
#             else "unknown_level"
#         )
#         folder_path = f"student/{year_level}/{user.first_name}_{user.last_name}"

#     elif instance.document and instance.document.teacher:
#         user = instance.document.teacher.user
#         folder_path = f"teacher/{user.first_name}_{user.last_name}"

#     elif instance.document and instance.document.guardian:
#         user = instance.document.guardian.user
#         folder_path = f"guardian/{user.first_name}_{user.last_name}"

#     elif instance.document and instance.document.office_staff:
#         user = instance.document.office_staff.user
#         folder_path = f"office_staff/{user.first_name}_{user.last_name}"

#     else:
#         folder_path = "unknown"

#     # Debugging print statements
#     print(f"DEBUG: ROLE DETECTED: {folder_path.split('/')[0]}")
#     print(f"DEBUG: FULL FOLDER PATH: {os.path.join(base_path, folder_path)}")
#     print(f"DEBUG: FILE PATH: {os.path.join(base_path, folder_path, filename)}")

#     return os.path.join(base_path, folder_path, filename)

#### commented as of 19 june25 at 11:11 PM till here










#### added as of 19 june25 at 11:11 PM from here

# import os

# def Document_folder(instance, filename):
#     try:
#         document = instance.document  # access the FK to Document
#     except Exception as e:
#         print(" No document attached to file:", e)
#         return f"Document_folder/unknown/{filename}"

#     base_path = "Document_folder"


#     if document.student:
#         user = document.student.user
#         year_level = (
#             document.student.studentyearlevel_set.first().level.level_name
#             if document.student.studentyearlevel_set.exists()
#             else "unknown_level"
#         )
#         folder_path = f"student/{year_level}/{user.first_name}_{user.last_name}"
#     elif document.teacher:
#         user = document.teacher.user
#         folder_path = f"teacher/{user.first_name}_{user.last_name}"
#     elif document.guardian:
#         user = document.guardian.user
#         folder_path = f"guardian/{user.first_name}_{user.last_name}"
#     elif document.office_staff:
#         user = document.office_staff.user
#         folder_path = f"office_staff/{user.first_name}_{user.last_name}"
#     else:
#         folder_path = "unknown"

#     return os.path.join(base_path, folder_path, filename)


from datetime import datetime
import os
from datetime import datetime

def Document_folder(instance, filename):
    try:
        document = instance.document  # access the FK to Document
    except Exception as e:
        print(" No document attached to file:", e)
        return f"Document_folder/unknown/{filename}"

    base_path = "Document_folder"

    if document.student:
        user = document.student.user
        year_level = (
            document.student.student_year_levels.first().level.level_name
            if document.student.student_year_levels.exists()
            else "unknown_level"
        )
        folder_path = f"student/{year_level}/{user.first_name}_{user.last_name}"
    elif document.teacher:
        user = document.teacher.user
        folder_path = f"teacher/{user.first_name}_{user.last_name}"
    elif document.guardian:
        user = document.guardian.user
        folder_path = f"guardian/{user.first_name}_{user.last_name}"
    elif document.office_staff:
        user = document.office_staff.user
        folder_path = f"office_staff/{user.first_name}_{user.last_name}"
    else:
        folder_path = "unknown"

    return os.path.join(base_path, folder_path, filename)


# ---------------------- Exam Paper
def clean_name(name):
    if not name:
        return "unknown"
    return name.replace("\xa0", "_").replace(" ", "_")


def ExamPaper_folder(instance, filename):
    try:
        paper = instance  
        teacher = paper.teacher.user
        teacher_name = f"{teacher.first_name}_{teacher.last_name}"
    except Exception as e:
        print("Error accessing teacher:", e)
        teacher_name = "unknown_teacher"

    try:
        # class_name = paper.exam.year_level.level_name
        class_name = paper.year_level.level_name

    except Exception as e:
        print("Error accessing class name:", e)
        class_name = "unknown_class"

    try:
        subject_name = paper.subject.subject_name
        school_year = paper.term.year.year_name
        exam_type = paper.exam_type.name

        new_filename = f"{subject_name}-{school_year}-{exam_type}{os.path.splitext(filename)[1]}"
    except Exception as e:
        print("Error building file name:", e)
        new_filename = filename

    folder_path = os.path.join("ExamPaper_folder", teacher_name, class_name)
    full_path = os.path.join(folder_path, new_filename)

    print("file path:", full_path)  
    return full_path

# ------------------ File Download's
from django.http import FileResponse
from rest_framework.response import Response
from django.core.exceptions import ValidationError

def get_file_response(file_field, file_label="file"):
    if file_field and hasattr(file_field, "path") and os.path.exists(file_field.path):
        response = FileResponse(open(file_field.path, 'rb'))
        response["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_field.name)}"'
        return response
    return Response({"error": f"{file_label} not found."}, status=404)





# ---------------------  Income and Expense 

def income_attachments(instance, filename):
    category_name = instance.category.name.replace(" ", "_").lower()
    return os.path.join(
        "income_attachments",
        str(datetime.now().year),               
        str(datetime.now().month).zfill(2),       
        f"{category_name}_{filename}"  
        )


def expense_attachments(instance, filename):
    category_name = instance.category.name.replace(" ", "_").lower()
    year = instance.school_year.start_date.year if instance.school_year else datetime.now().year
    # month = instance.expense_date.month if instance.expense_date else datetime.now().month
    month_name = instance.expense_date.strftime("%B") if instance.expense_date else datetime.now().strftime("%B")

    return os.path.join(
        "expense_attachments",
        str(year),
        month_name,  
        f"{category_name}_{filename}"
    )



from django.core.mail import send_mail
from django.conf import settings

def send_email_notification(to_email, subject, message):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=False,
    )


def normalize_phone(num):
    num = str(num).strip()

    # remove spaces and weird chars
    num = num.replace(" ", "").replace("-", "")

    # ensure it starts with +91 only once
    if num.startswith("0"):
        num = num[1:]   # remove leading 0

    if not num.startswith("+91"):
        num = "+91" + num

    return num

    
from twilio.rest import Client 

def send_whatsapp(message_text, phone_number):
    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    try:
        phone = normalize_phone(phone_number)

        msg = client.messages.create(
            from_=settings.TWILIO_WHATSAPP_NUMBER,
            body=message_text,
            to=f"whatsapp:{phone}"
        )
        return {"number": phone, "status": "sent", "sid": msg.sid}

    except Exception as e:
        return {"number": phone, "status": "failed", "error": str(e)}
  



def reportcard_attachments(instance, filename):
    # Validate file type and size before returning path
    ALLOWED_EXT = {'.pdf', '.jpg', '.jpeg', '.png'}
    MAX_SIZE = 5 * 1024 * 1024  # 5 MB

    # extension check
    _, ext = os.path.splitext(filename)
    if ext.lower() not in ALLOWED_EXT:
        raise ValidationError(
            f"Unsupported file type '{ext}'. Allowed types: {', '.join(sorted(ALLOWED_EXT))}."
        )

    # try to access uploaded file size (UploadedFile on instance.file)
    uploaded_file = getattr(instance, 'file', None)
    try:
        file_size = getattr(uploaded_file, 'size', None)
    except Exception:
        file_size = None

    if file_size and file_size > MAX_SIZE:
        raise ValidationError(f"File size exceeds the allowed limit of {MAX_SIZE // (1024*1024)} MB.")

    # folder structure: reportcard_attachments/<year>/<level>/<student_name_scholar_no>/<filename>
    student = getattr(instance, 'student', None)

    year_part = getattr(student.year, 'year_name', datetime.now().year) if student else datetime.now().year
    level_part = getattr(student.level, 'level_name', 'unknown_level') if student else 'unknown_level'

    student_obj = getattr(student, 'student', None) if student else None
    if student_obj:
        user = getattr(student_obj, 'user', None)
        scholar_no = getattr(student_obj, 'scholar_number', None)
        name_part = None
        if user:
            fname = getattr(user, 'first_name', '') or ''
            lname = getattr(user, 'last_name', '') or ''
            name_part = f"{fname}_{lname}".strip('_') if (fname or lname) else None

        if scholar_no and name_part:
            student_part = f"{name_part}_{scholar_no}"
        elif name_part:
            student_part = name_part
        elif scholar_no:
            student_part = f"student_{scholar_no}"
        else:
            student_part = f"student_{getattr(student_obj, 'id', 'unknown')}"
    else:
        student_part = f"student_{getattr(student, 'id', 'unknown')}"

    folder = os.path.join(
        'reportcard_attachments',
        clean_name(year_part),
        clean_name(level_part),
        clean_name(student_part)
    )

    return os.path.join(folder, filename)


# ---------------------------------- Fee Due Year Utility --------------------------------------------
from datetime import date
from decimal import Decimal
from django.utils import timezone

def get_fee_due_year(school_year, month):
    # For a July-start academic year: Jul–Dec → start year, Jan–Jun → end year
    if month >= 7:
        return int(school_year.start_date.year)
    return int(school_year.end_date.year)


def calculate_penalty(fee_type, school_year, month):
    if fee_type.lower() != "tuition fee":
        return Decimal("0.00")

    today = timezone.now().date()
    today_month = today.month
    today_year = today.year

    # Determine the correct year for this month based on TODAY's date
    # If we're currently in months 1-6, fees starting July are for THIS year
    # If we're currently in months 7-12, fees starting July next year are for NEXT year
    if today_month <= 6:
        # Currently Jan-June
        if month >= 7:
            due_year = today_year
        else:
            due_year = today_year + 1
    else:
        # Currently Jul-Dec
        if month >= 7:
            due_year = today_year
        else:
            due_year = today_year + 1
    
    due_date = date(due_year, month, 15)

    # Only apply penalty if the due date has actually passed
    if today > due_date:
        return Decimal("25.00")

    return Decimal("0.00")

