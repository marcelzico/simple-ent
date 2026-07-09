from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg, Q, F, Max, Min, StdDev, Variance
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, ExtractHour
from django.utils import timezone
from datetime import timedelta, date, datetime
import json
from decimal import Decimal
import numpy as np
from collections import defaultdict
import pandas as pd
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


# Import your models
from utilisateur.models import User
from lecon.models import Unite, Chapter
from student.models import StudentProfile
# from subscriptions.models import Subscription, Payment, Feature
from quizzes.models import MCQResult, QAResult, TrueFalseResult, MCQAttempt, QAAttempt
from lessoncopy.models import StudySession, Copy, UserAnnotation




def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_superuser or user.is_staff


# AJAX endpoint for filtering without page reload
@login_required
@user_passes_test(is_admin)
def dashboard_user_filter_ajax(request):
    """Return filtered user data as JSON for AJAX requests"""
    from django.http import JsonResponse
    
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    level_filter = request.GET.get('level', 'all')
    search_query = request.GET.get('search', '')
    page = request.GET.get('page', 1)
    
    # Apply same filters as main view
    users_queryset = User.objects.select_related('student_profile').all()
    
    if role_filter == 'student':
        users_queryset = users_queryset.filter(is_student=True)
    elif role_filter == 'staff':
        users_queryset = users_queryset.filter(is_staff=True, is_superuser=False)
    elif role_filter == 'admin':
        users_queryset = users_queryset.filter(is_superuser=True)
    elif role_filter == 'other':
        users_queryset = users_queryset.filter(is_student=False, is_staff=False, is_superuser=False)
    
    today = timezone.now().date()
    ninety_days_ago = today - timedelta(days=90)
    if status_filter == 'active':
        users_queryset = users_queryset.filter(last_login__date__gte=ninety_days_ago)
    elif status_filter == 'inactive':
        users_queryset = users_queryset.filter(Q(last_login__date__lt=ninety_days_ago) | Q(last_login__isnull=True))
    elif status_filter == 'never_logged':
        users_queryset = users_queryset.filter(last_login__isnull=True)
    
    if level_filter != 'all' and role_filter in ['all', 'student']:
        users_queryset = users_queryset.filter(student_profile__level=level_filter)
    
    if search_query:
        users_queryset = users_queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query)
        )
    
    total_count = users_queryset.count()
    users_queryset = users_queryset.order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(users_queryset, 15)
    try:
        users_page = paginator.page(page)
    except:
        users_page = paginator.page(1)
    
    users_list = []
    for user in users_page:
        # Get student level display
        student_level_display = '-'
        if hasattr(user, 'student_profile') and user.student_profile and user.student_profile.level:
            level_dict = dict(StudentProfile.LEVEL_CHOICES)
            student_level_display = level_dict.get(user.student_profile.level, user.student_profile.level)
        
        users_list.append({
            'id': user.id,
            'full_name': user.display_name,
            'email': user.email,
            'role': user.get_primary_role(),
            'role_display': 'Étudiant' if user.is_student else 'Personnel' if user.is_staff else 'Admin' if user.is_superuser else 'Utilisateur',
            'date_joined': user.date_joined.strftime('%d/%m/%Y'),
            'last_login': user.last_login.strftime('%d/%m/%Y') if user.last_login else 'Jamais',
            'is_active': user.is_active,
            'student_level': student_level_display,
        })
    
    return JsonResponse({
        'users': users_list,
        'total_count': total_count,
        'has_next': users_page.has_next(),
        'has_previous': users_page.has_previous(),
        'current_page': users_page.number,
        'total_pages': paginator.num_pages,
    })


@login_required
@user_passes_test(is_admin)
def dashboard_user_section(request):
    """
    Main view for user management section of dashboard
    """
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    sixty_days_ago = today - timedelta(days=60)
    ninety_days_ago = today - timedelta(days=90)
    
    # Get filter parameters from request
    role_filter = request.GET.get('role', 'all')
    status_filter = request.GET.get('status', 'all')
    level_filter = request.GET.get('level', 'all')
    search_query = request.GET.get('search', '')
    
    # === Base queryset with filters ===
    users_queryset = User.objects.select_related('student_profile').all()
    
    # Apply role filter
    if role_filter == 'student':
        users_queryset = users_queryset.filter(is_student=True)
    elif role_filter == 'staff':
        users_queryset = users_queryset.filter(is_staff=True, is_superuser=False)
    elif role_filter == 'admin':
        users_queryset = users_queryset.filter(is_superuser=True)
    elif role_filter == 'other':
        users_queryset = users_queryset.filter(is_student=False, is_staff=False, is_superuser=False)
    
    # Apply status filter
    if status_filter == 'active':
        users_queryset = users_queryset.filter(last_login__date__gte=ninety_days_ago)
    elif status_filter == 'inactive':
        users_queryset = users_queryset.filter(Q(last_login__date__lt=ninety_days_ago) | Q(last_login__isnull=True))
    elif status_filter == 'never_logged':
        users_queryset = users_queryset.filter(last_login__isnull=True)
    elif status_filter == 'email_verified':
        users_queryset = users_queryset.filter(is_active=True)
    
    # Apply level filter (for students)
    if level_filter != 'all' and role_filter in ['all', 'student']:
        users_queryset = users_queryset.filter(
            student_profile__level=level_filter
        )
    
    # Apply search
    if search_query:
        users_queryset = users_queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    # === 1. User Overview Cards with CORRECTED calculations ===
    total_users = User.objects.count()
    total_students = User.objects.filter(is_student=True).count()
    total_staff = User.objects.filter(is_staff=True, is_superuser=False).count()
    total_admins = User.objects.filter(is_superuser=True).count()
    
    # CORRECTED: New users this month (current month to date)
    first_day_of_current_month = today.replace(day=1)
    new_users_current_month = User.objects.filter(
        date_joined__date__gte=first_day_of_current_month
    ).count()
    
    # CORRECTED: Previous month users (full previous month)
    first_day_of_previous_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    new_users_previous_month = User.objects.filter(
        date_joined__date__gte=first_day_of_previous_month,
        date_joined__date__lte=last_day_of_previous_month
    ).count()
    
    # CORRECTED: Calculate user growth percentage
    user_growth = 0
    if new_users_previous_month > 0:
        user_growth = round(((new_users_current_month - new_users_previous_month) / new_users_previous_month) * 100, 1)
    elif new_users_current_month > 0:
        user_growth = 100  # 100% growth if from 0 to positive
    
    # CORRECTED: Active users (logged in within last 90 days)
    active_users = User.objects.filter(
        last_login__date__gte=ninety_days_ago
    ).count()
    
    # CORRECTED: Inactive users (not logged in for 90+ days OR never logged in)
    inactive_users = User.objects.filter(
        Q(last_login__date__lt=ninety_days_ago) | Q(last_login__isnull=True)
    ).count()
    
    # Email verified count
    email_verified_count = User.objects.filter(is_active=True).count()
    
    # === 2. Role Distribution Data ===
    role_distribution = {
        'students': total_students,
        'staff': total_staff,
        'admins': total_admins,
        'other': total_users - (total_students + total_staff + total_admins)
    }
    
    # === 3. Recent Registrations with Pagination ===
    users_queryset = users_queryset.order_by('-date_joined')
    
    # Pagination (15 per page)
    paginator = Paginator(users_queryset, 15)
    page = request.GET.get('page', 1)
    
    try:
        users_page = paginator.page(page)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)
    
    # Prepare data for table
    users_data = []
    for user in users_page:
        student_level_display = '-'
        student_level_raw = None
        institution = '-'
        
        if hasattr(user, 'student_profile') and user.student_profile:
            student_level_raw = user.student_profile.level
            if student_level_raw:
                level_dict = dict(StudentProfile.LEVEL_CHOICES)
                student_level_display = level_dict.get(student_level_raw, student_level_raw)
            institution = user.student_profile.institution or '-'
        
        users_data.append({
            'id': user.id,
            'full_name': user.display_name,
            'username': user.username,
            'email': user.email,
            'phone': user.phone_number if user.phone_number else '-',
            'role': user.get_primary_role(),
            'role_display': 'Étudiant' if user.is_student else 'Personnel' if user.is_staff else 'Admin' if user.is_superuser else 'Utilisateur',
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'is_active': user.is_active,
            'student_level_display': student_level_display,
            'institution': institution,
        })
    
    # === 4. User Activity Summary (CORRECTED) ===
    # Users inactive for >30 days (but not necessarily 90)
    inactive_thirty_days = User.objects.filter(
        last_login__date__lte=today - timedelta(days=30),
        last_login__date__gt=today - timedelta(days=90),
        is_active=True
    ).count()
    
    # Never logged in users
    never_logged_in = User.objects.filter(last_login__isnull=True, is_active=True).count()
    
    # Last 7 days activity
    last_week = today - timedelta(days=7)
    weekly_active = User.objects.filter(last_login__date__gte=last_week).count()
    
    activity_summary = {
        'weekly_active': weekly_active,
        'inactive_thirty_days': inactive_thirty_days,
        'never_logged_in': never_logged_in,
        'total_inactive': inactive_users,
    }
    
    # === 5. Student-Specific Stats ===
    student_stats = {}
    student_level_choices = []
    
    if total_students > 0:
        students_by_level = StudentProfile.objects.values('level').annotate(
            count=Count('id')
        ).order_by('-count')
        
        student_level_choices = []
        for level_code, level_label in StudentProfile.LEVEL_CHOICES:
            student_level_choices.append({
                'value': level_code,
                'label': level_label
            })
        
        active_students = StudentProfile.objects.filter(is_active_student=True).count()
        
        complete_profiles = StudentProfile.objects.filter(
            institution__isnull=False,
            level__isnull=False
        ).exclude(institution='').count()
        
        profile_completion = round((complete_profiles / total_students) * 100, 1) if total_students > 0 else 0
        
        students_by_institution = StudentProfile.objects.values('institution').annotate(
            count=Count('id')
        ).exclude(institution__isnull=True).exclude(institution='').order_by('-count')[:5]
        
        student_stats = {
            'by_level': list(students_by_level),
            'active_students': active_students,
            'inactive_students': total_students - active_students,
            'profile_completion': profile_completion,
            'by_institution': list(students_by_institution),
            'total': total_students,
        }
    
    # === 6. Monthly Registration Trends (COMPLETELY REWRITTEN) ===
    # Get last 6 complete months + current month to date
    monthly_labels = []
    monthly_data = []
    
    # Generate last 6 months
    for i in range(5, -1, -1):
        # Get the month
        target_date = today - timedelta(days=30 * i)
        year = target_date.year
        month = target_date.month
        
        # Get first and last day of that month
        first_day = target_date.replace(day=1)
        if month == 12:
            last_day = target_date.replace(year=year+1, month=1, day=1) - timedelta(days=1)
        else:
            last_day = target_date.replace(month=month+1, day=1) - timedelta(days=1)
        
        # If it's current month, only count up to today
        if i == 0:
            last_day = today
        
        # Count users registered in this period
        month_count = User.objects.filter(
            date_joined__date__gte=first_day,
            date_joined__date__lte=last_day
        ).count()
        
        # Format label
        month_label = target_date.strftime('%B %Y')
        monthly_labels.append(month_label)
        monthly_data.append(month_count)
    
    # === 7. Student Level Stats ===
    student_level_labels = []
    student_level_counts = []
    level_display_dict = dict(StudentProfile.LEVEL_CHOICES)
    
    for level_data in student_stats.get('by_level', []):
        if level_data['level']:
            level_display = level_display_dict.get(level_data['level'], level_data['level'])
            student_level_labels.append(level_display)
            student_level_counts.append(level_data['count'])
    
    filter_counts = {
        'all': total_users,
        'student': total_students,
        'staff': total_staff,
        'admin': total_admins,
        'active': active_users,
        'inactive': inactive_users,
    }
    
    # For debugging - you can remove these in production
    print(f"DEBUG - Current month new users: {new_users_current_month}")
    print(f"DEBUG - Previous month new users: {new_users_previous_month}")
    print(f"DEBUG - User growth: {user_growth}%")
    print(f"DEBUG - Monthly data: {monthly_data}")
    print(f"DEBUG - Monthly labels: {monthly_labels}")
    
    context = {
        'section_title': "Gestion des Utilisateurs",
        'current_role_filter': role_filter,
        'current_status_filter': status_filter,
        'current_level_filter': level_filter,
        'current_search': search_query,
        'student_level_choices': student_level_choices,
        'filter_counts': filter_counts,
        'total_users': total_users,
        'total_students': total_students,
        'total_staff': total_staff,
        'total_admins': total_admins,
        'new_users_month': new_users_current_month,
        'user_growth': user_growth,
        'active_users': active_users,
        'inactive_users': inactive_users,
        'email_verified_count': email_verified_count,
        'role_distribution_labels': ['Étudiants', 'Personnel', 'Administrateurs', 'Autres'],
        'role_distribution_data': [
            role_distribution['students'],
            role_distribution['staff'],
            role_distribution['admins'],
            role_distribution['other']
        ],
        'role_distribution_colors': ['#36A2EB', '#FFCE56', '#FF6384', '#9966FF'],
        'monthly_labels': monthly_labels,
        'monthly_data': monthly_data,
        'student_level_labels': student_level_labels,
        'student_level_counts': student_level_counts,
        'recent_users': users_data,
        'users_page': users_page,
        'paginator': paginator,
        'activity_summary': activity_summary,
        'student_stats': student_stats,
        'students_by_institution': student_stats.get('by_institution', []),
        'today': today,
    }
    
    # Handle AJAX request for filtering
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        from django.template.loader import render_to_string
        
        html = render_to_string('dashboard/partials/user_section_table_only.html', context, request=request)
        return JsonResponse({
            'success': True,
            'html': html,
            'total_count': users_page.paginator.count,
        })
    
    return render(request, 'dashboard/partials/user_section.html', context)


