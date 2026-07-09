from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    User
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'gender', 'email', 'phone_number', 'is_student', 'is_teacher', 'is_staff')
    list_filter = ('is_student', 'is_staff', 'is_teacher', 'is_superuser')
    search_fields = ('username', 'email', 'phone_number', 'first_name', 'last_name')
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_student', 'is_teacher',
                                   'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    



