

# ***********************************2222**************************


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



import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

def send_email_notification(to_email, subject, message):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
    


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


#---------------------------- Transfer Certificate (TC) Utilities --------------------------------------------


'''------------------------------------Transfer Certificates Template--------------------------------------------'''
"""
POST /d/GenerateTC/

Accepts the filled Transfer Certificate form fields (from the frontend modal),
renders them into a PDF that visually matches your physical TC layout, 
and returns that PDF directly in the response.

The frontend does NOT need to save this anywhere separately — it just
takes the returned PDF blob and attaches it as `files` in the existing
POST /d/Document/ call, alongside:
    document_types = <id of "Transfer Certificate" type>
    identities     = tc_no
    student        = <student id>

So this endpoint only generates the file. Existing DocumentView
handles the actual save — nothing there needs to change.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from student.models import Student, StudentYearLevel

REQUIRED_FIELDS = ['tc_no', 'scholar_no', 'student_name', 'date_of_birth', 'from_date', 'to_date']

# Maps our TC field name -> the exact DocumentType.name used as a fallback
# source when the Student model field itself is empty.
DOCUMENT_TYPE_FALLBACKS = {
    'aadhaar_no': 'Aadhaar Number',
    'apaar_id': 'Apaar ID',
    'fmid': 'Family ID',
    'pen_no': 'PEN Number',
    'sssm_id': 'SSSM ID',
}


def _prefill_from_student(student_id, data):
    """
    Fill in anything the frontend didn't send, using the Student record.
    Anything the frontend already sent (user edited it) takes priority.
    """
    from .models import Admission

    if not student_id:
        return data

    student = Student.objects.filter(id=student_id, is_active=True).select_related('user').first()
    if not student:
        return data
    
    student_year = (
        StudentYearLevel.objects.filter(student_id=student_id)
        .select_related("level", "year")
        .order_by("-id")
        .first()
    )
    admission = Admission.objects.filter(student=student_year.student).first()

    defaults = {
        'student_name': f"{student.user.first_name} {student.user.last_name}".strip(),
        'father_name': student.father_name,
        'mother_name': student.mother_name,
        'date_of_birth': student.date_of_birth.strftime('%d-%m-%Y') if student.date_of_birth else '',
        "year_level": student_year.level.level_name if student_year and student_year.level else "",
        "school_year": student_year.year.year_name if student_year and student_year.year else "",
        'scholar_no': student.scholar_number,
        'aadhaar_no': student.aadhaar_number,
        'fmid': student.FMID_number,
        'apaar_id': student.apaar_number,
        'pen_no': student.PEN_number,
        'admission_date': admission.admission_date,
    }

    for key, val in defaults.items():
        if not data.get(key) and val:
            data[key] = val

    return data


def _prefill_from_documents(student_id, data):
    """
    Backup source, used only for whatever is STILL missing after the
    Student model pass — e.g. the Student record never had `aadhaar_number`
    filled in, but a parent uploaded an "Aadhaar Number" document earlier,
    and that document's `identities` value holds the actual number.
    """
    from .models import Document
    if not student_id:
        return data

    still_missing = [f for f in DOCUMENT_TYPE_FALLBACKS if not data.get(f)]
    if not still_missing:
        return data

    type_names = [DOCUMENT_TYPE_FALLBACKS[f] for f in still_missing]

    docs = (
        Document.objects.filter(
            student_id=student_id,
            document_types__name__in=type_names,
            is_active=True,
        )
        .prefetch_related('document_types')
        .distinct()
    )

    # Build type_name -> identity value, in case a student has multiple docs
    by_type = {}
    for doc in docs:
        if not doc.identities:
            continue
        for dt in doc.document_types.all():
            if dt.name in type_names and dt.name not in by_type:
                # identities can be a comma-joined string if multiple were
                # submitted together — take the first meaningful value
                by_type[dt.name] = doc.identities.split(',')[0].strip()

    for field in still_missing:
        type_name = DOCUMENT_TYPE_FALLBACKS[field]
        if type_name in by_type:
            data[field] = by_type[type_name]

    return data

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_transfer_certificate_data(request):
    student_id = request.query_params.get("student_id")

    if not student_id:
        return Response(
            {"error": "student_id is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    student = Student.objects.filter(id=student_id).first()
    if not student:
        return Response(
            {"error": "Student not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    data = {"student_id": student_id}

    # 1. Fill from Student model
    data = _prefill_from_student(student_id, data)

    # 2. Fill remaining missing fields from Document
    data = _prefill_from_documents(student_id, data)

    return Response(data, status=status.HTTP_200_OK)


def is_tc_document_type(doc_type):
    """
    Check if a DocumentType instance or its name represents a Transfer Certificate / TC.
    """
    if not doc_type:
        return False
    name = (getattr(doc_type, 'name', None) or str(doc_type) or '').strip().lower()
    if 'transfer' in name or name == 'tc':
        return True
    import re
    tokens = re.split(r'[^a-zA-Z0-9]+', name)
    return 'tc' in tokens


def is_tc_document(document):
    """
    Check if a Document instance has any document type that is a TC.
    """
    if not document:
        return False
    return any(is_tc_document_type(dt) for dt in document.document_types.all())


def deactivate_student_on_tc_issue(student, tc_document=None, reason="TC Issued"):
    """
    Deactivates a student when a TC (Transfer Certificate) is issued.
    Sets reason to "TC Issued", deactivates user, admissions, addresses,
    banking details, creates UserStatusLog, and deactivates other non-TC documents.
    """
    if not student:
        return

    from django.utils import timezone
    from django.db import transaction, models
    from authentication.models import UserStatusLog
    from director.models import Admission, Address, BankingDetail, Document

    with transaction.atomic():
        # 1. Deactivate student
        student.is_active = False
        student.save(update_fields=['is_active'])

        # 2. Deactivate user and set deactivation reason
        user = student.user
        if user:
            user.is_active = False
            user.deactivation_reason = reason
            user.deactivation_date = timezone.now()
            user.reactivation_date = None
            user.save(update_fields=['is_active', 'deactivation_reason', 'deactivation_date', 'reactivation_date'])

            # 3. Deactivate addresses
            Address.objects.all_including_inactive().filter(user=user).update(is_active=False)

            # 4. Deactivate banking details
            BankingDetail.objects.all_including_inactive().filter(user=user).update(is_active=False)

            # 5. Log status change
            UserStatusLog.objects.create(
                user=user,
                status='TERMINATED',
                reason=reason
            )

        # 6. Deactivate admissions
        Admission.objects.all_including_inactive().filter(student=student).update(is_active=False)

        # 7. Deactivate non-TC documents
        non_tc_docs = Document.objects.all_including_inactive().filter(student=student)
        if tc_document and getattr(tc_document, 'id', None):
            non_tc_docs = non_tc_docs.exclude(id=tc_document.id)
        non_tc_docs = non_tc_docs.exclude(
            models.Q(document_types__name__icontains='transfer') |
            models.Q(document_types__name__iexact='tc')
        )
        non_tc_docs.update(is_active=False)

        # 8. Ensure TC document itself remains active
        if tc_document and getattr(tc_document, 'id', None) and not tc_document.is_active:
            tc_document.is_active = True
            tc_document.save(update_fields=['is_active'])


def check_and_deactivate_student_for_tc(document, reason="TC Issued"):
    """
    Given a Document instance, checks if it is for a student and includes a TC document type.
    If so, deactivates the student with the specified reason.
    """
    if not document or not document.student_id:
        return

    if is_tc_document(document):
        from student.models import Student
        student = Student.objects.all_including_inactive().filter(id=document.student_id).first()
        if student:
            deactivate_student_on_tc_issue(student, tc_document=document, reason=reason)
