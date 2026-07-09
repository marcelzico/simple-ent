from django.contrib import admin
from . models import TeacherDashboardWidget, TeacherProfile, NotificationPreference

# Register your models here.
admin.site.register(TeacherProfile)
admin.site.register(TeacherDashboardWidget)
admin.site.register(NotificationPreference)
