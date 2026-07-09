from django.contrib import admin
from django import forms
from .models import Unite, Chapter
from utilisateur.models import User
from django.utils import timezone


# Register your models here.

@admin.register(Chapter)
class ChapterAdmin (admin.ModelAdmin):
    list_display = ('ue', 'title', 'prof', 'updated_at')
    # list_filter = ('ue', 'title')
    search_fields = ('ue', 'title', 'prof')
    ordering = ['ue', 'title']
    sortable_by = ['ue', 'title', 'prof']

class ChapterInline (admin.TabularInline):
    model = Chapter


@admin.register(Unite)
class UniteAdmin(admin.ModelAdmin):
    inlines= [ChapterInline]
    list_display = ('title', 'level', 'semester', 'created_at')
    # list_filter = ('title', 'level')
    search_fields = ('title', 'level')
    ordering = ['level', 'level']


