from django.contrib import admin
from .models import TeacherYearLevel ,TeacherAttendance,SubstituteAssignment

admin.site.register(TeacherYearLevel)
admin.site.register(TeacherAttendance)
admin.site.register(SubstituteAssignment)

