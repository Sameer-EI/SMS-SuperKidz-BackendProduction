from django.contrib import admin
from .models import *

<<<<<<< HEAD
admin.site.register(User)
=======
from .models import ErrorLog
admin.site.register(User)


@admin.register(ErrorLog)
class ErrorLogAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'method', 'error_type', 'status_code', 'timestamp']
    search_fields = ['error_message', 'endpoint', 'user__email']
>>>>>>> d5cd230de01448c3929235e73eea35e13e4d28fb
