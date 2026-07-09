from django.contrib import admin
from . models import StudentProfile
# Register your models here.

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'institution','created_at')
    list_filter = ('level', 'created_at')
    search_fields = ('user__username', 'user__email', 'user__first_name', 'user__last_name', 'institution')
    raw_id_fields = ('user',)
