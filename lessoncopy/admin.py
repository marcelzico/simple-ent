from django.contrib import admin
from .models import Copy, Importer, Resume, ResumeIA, UserAnnotation, StudySession

# Register your models here.

@admin.register(Copy)
class CopyAdmin(admin.ModelAdmin):
    '''Admin View for Copy'''

    list_display = ('chapter','heading', 'is_qe')
    list_filter = ('chapter','heading', 'is_qe')
    # raw_id_fields = ('',)
    # readonly_fields = ('',)
    # search_fields = ('',)
    # date_hierarchy = ''
    ordering = ('created_at', 'chapter')


@admin.register(Importer)
class  ImporterAdmin (admin.ModelAdmin):
    list_display = ('chapter', 'title', 'file', 'uploaded_at')
    list_filter = ('chapter','file', 'uploaded_at')
    ordering = ('uploaded_at', 'chapter')


# admin.site.register (Copy)
# admin.site.register (Importer)
admin.site.register (ResumeIA)
admin.site.register (Resume)
admin.site.register (StudySession)
admin.site.register (UserAnnotation) 