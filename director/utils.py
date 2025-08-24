

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

def get_file_response(file_field, file_label="file"):
    if file_field and hasattr(file_field, "path") and os.path.exists(file_field.path):
        response = FileResponse(open(file_field.path, 'rb'))
        response["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_field.name)}"'
        return response
    return Response({"error": f"{file_label} not found."}, status=404)



#------------------------------------------REPORTCARD Util----------------------------------------------------
from collections import defaultdict
from .models import *

def calculate_subject_summary(subjects_data):
    required_exams = {"sa1", "sa2"}
    subject_marks = defaultdict(dict)  # subject -> {exam_type: mark}

    # Collect marks
    for exam in subjects_data:
        exam_type = exam.get("exam_type", "").lower()
        if exam_type not in required_exams:
            continue

        for subject, mark in exam.get("subjects", {}).items():
            try:
                subject_marks[subject][exam_type] = float(mark)
            except (TypeError, ValueError):
                continue

    # Validate missing exam types per subject
    missing_data = {
        subject: list(required_exams - marks.keys())
        for subject, marks in subject_marks.items()
        if required_exams - marks.keys()
    }

    if missing_data:
        return {
            "subject_avg": {
                "error": "Some subjects are missing marks for required exams.",
                "missing_exam_data": {
                    subject: [x.upper() for x in exams]
                    for subject, exams in missing_data.items()
                }
            },
            "total_marks": 0,
            "max_marks": 0,
            "percentage": 0,
            "grade": "F",
            "supplementary_in": []
        }

    if not subject_marks:
        return {
            "subject_avg": {
                "error": "SA1&SA2 Missing"
            },
            "total_marks": 0,
            "max_marks": 0,
            "percentage": 0,
            "grade": "F",
            "supplementary_in": []
        }

    # Calculate per-subject percent
    subject_avg = {}
    supplementary_in = []
    
    for subject, exams in subject_marks.items():
        sa1 = exams.get("sa1", 0)
        sa2 = exams.get("sa2", 0)
        obtained = sa1 + sa2

        # Scale: max combined SA1+SA2 is 200 → scale to 100
        percent = round((obtained / 200) * 100, 2)
        subject_avg[subject] = round(obtained / 2, 2)  # still averaging for display

        if percent < 40:
            supplementary_in.append(subject)

    # Final totals
    total_obtained = sum(subject_avg.values())
    subject_count = len(subject_avg)
    total_possible = subject_count * 100
    percentage = round((total_obtained / total_possible) * 100, 2) if total_possible else 0

    # Grade logic
    if percentage >= 90:
        grade = "A++"
    elif percentage >= 80:
        grade = "A+"
    elif percentage >= 70:
        grade = "A"
    elif percentage >= 60:
        grade = "B"
    elif percentage >= 50:
        grade = "C"
    elif percentage >= 40:
        grade = "D"
    else:
        grade = "F"

    return {
        "subject_avg": subject_avg,
        "total_marks": total_obtained,
        "max_marks": total_possible,
        "percentage": percentage,
        "grade": grade,
        "supplementary_in": supplementary_in
    }


def income_attachments(instance, filename):
    category_name = instance.category.name.replace(" ", "_").lower()
    return os.path.join(
        "income_attachments",
        str(datetime.now().year),                  # Year
        str(datetime.now().month).zfill(2),        # Month
        f"{category_name}_{filename}"  # FileName = id_category_filename
    )