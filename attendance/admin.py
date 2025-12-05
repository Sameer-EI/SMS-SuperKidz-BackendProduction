from django.contrib import admin
from attendance.models import *

# admin.site.register(AttendanceSession)
admin.site.register(StudentAttendance)
admin.site.register(Holiday)
admin.site.register(SchoolHoliday)
admin.site.register(SchoolEvent)
admin.site.register(OfficeStaffAttendance)