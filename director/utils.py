

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

