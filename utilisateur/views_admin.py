# utilisateur/views_admin.py - FICHIER COMPLET
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from datetime import datetime, timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import os
import subprocess
import psutil
from django.conf import settings
from .decorators import admin_required, staff_only, superuser_only, log_admin_activity
from .models import (
    User, StudentProfile, TeacherProfile,
    AdminDashboardModule, AdminActivityLog,
    AdminPermission
)
from administration.models import AdminDashboardModule, AdminActivityLog, AdminPermission, AdminProfile


# ======================
# TABLEAU DE BORD ADMIN
# ======================

@login_required
@admin_required
def admin_dashboard(request):
    """
    Tableau de bord principal pour staff et superusers
    """
    user = request.user
    
    # Récupérer les modules accessibles
    accessible_modules = AdminDashboardModule.objects.filter(
        is_active=True,
        is_visible=True
    ).order_by('order')
    
    # Filtrer selon les permissions de l'utilisateur
    if not user.is_superuser:
        accessible_modules = [
            module for module in accessible_modules 
            if module.user_has_access(user)
        ]
    
    # Statistiques globales
    stats = {}
    
    if user.is_superuser or user.has_perm('users.view_users'):
        stats['total_users'] = User.objects.count()
        stats['new_users_today'] = User.objects.filter(
            date_joined__date=timezone.now().date()
        ).count()
        stats['new_users_week'] = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).count()
    
    if user.is_superuser or user.has_perm('users.view_students'):
        stats['total_students'] = StudentProfile.objects.count()
        stats['active_students'] = StudentProfile.objects.filter(
            is_active_student=True
        ).count()
        stats['premium_students'] = StudentProfile.objects.filter(
            is_premium=True
        ).count()
    
    if user.is_superuser or user.has_perm('users.view_teachers'):
        stats['total_teachers'] = TeacherProfile.objects.count()
        stats['verified_teachers'] = TeacherProfile.objects.filter(
            is_verified=True
        ).count()
        stats['active_teachers'] = TeacherProfile.objects.filter(
            is_active_teacher=True
        ).count()
    
    if user.is_superuser or user.has_perm('users.view_enrollments'):
        stats['total_enrollments'] = Enrollment.objects.count()
        stats['active_enrollments'] = Enrollment.objects.filter(
            is_active=True
        ).count()
    
    # Activités récentes
    recent_activities = AdminActivityLog.objects.all().order_by('-created_at')[:10]
    
    # Graphique des inscriptions (30 derniers jours)
    enrollment_chart_data = []
    if user.is_superuser or user.has_perm('users.view_analytics'):
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        dates = [start_date + timedelta(days=i) for i in range(31)]
        
        daily_enrollments = Enrollment.objects.filter(
            enrolled_date__date__gte=start_date,
            enrolled_date__date__lte=end_date
        ).values('enrolled_date__date').annotate(
            count=Count('id')
        ).order_by('enrolled_date__date')
        
        enrollment_dict = {item['enrolled_date__date']: item['count'] for item in daily_enrollments}
        
        enrollment_chart_data = [
            {
                'date': date.strftime('%Y-%m-%d'),
                'count': enrollment_dict.get(date, 0)
            }
            for date in dates
        ]
    
    context = {
        'user': user,
        'modules': accessible_modules,
        'stats': stats,
        'recent_activities': recent_activities,
        'enrollment_chart_data': json.dumps(enrollment_chart_data),
        'is_superuser': user.is_superuser,
    }
    
    return render(request, 'admin/dashboard.html', context)


# ======================
# GESTION DES UTILISATEURS
# ======================

@login_required
@admin_required(module='users')
def admin_users(request):
    """Gestion des utilisateurs"""
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = User.objects.all()
    
    # Filtres
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query)
        )
    
    if role_filter:
        if role_filter == 'student':
            users = users.filter(is_student=True)
        elif role_filter == 'teacher':
            users = users.filter(is_teacher=True)
        elif role_filter == 'staff':
            users = users.filter(is_staff=True)
        elif role_filter == 'superuser':
            users = users.filter(is_superuser=True)
    
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(users, 50)
    
    try:
        users_page = paginator.page(page)
    except PageNotAnInteger:
        users_page = paginator.page(1)
    except EmptyPage:
        users_page = paginator.page(paginator.num_pages)
    
    context = {
        'users': users_page,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'total_count': users.count(),
    }
    
    return render(request, 'admin/users/list.html', context)


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('view', model_name='User')
def admin_user_detail(request, user_id):
    """Détail d'un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    # Activités récentes
    recent_logins = AdminActivityLog.objects.filter(
        user=user,
        action='login'
    ).order_by('-created_at')[:5]
    
    admin_activities = AdminActivityLog.objects.filter(
        user=user
    ).exclude(action='login').order_by('-created_at')[:10]
    
    context = {
        'target_user': user,
        'student_profile': getattr(user, 'student_profile', None),
        'teacher_profile': getattr(user, 'teacher_profile', None),
        'recent_logins': recent_logins,
        'admin_activities': admin_activities,
    }
    
    return render(request, 'admin/users/detail.html', context)


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('update', model_name='User')
def admin_user_update(request, user_id):
    """Modifier un utilisateur"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        # Récupérer les données du formulaire
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        gender = request.POST.get('gender')
        is_active = request.POST.get('is_active') == 'on'
        is_staff = request.POST.get('is_staff') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        
        # Mettre à jour l'utilisateur
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.phone_number = phone_number
        user.gender = gender
        user.is_active = is_active
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save()
        
        messages.success(request, f'Utilisateur {user.username} mis à jour avec succès.')
        return redirect('admin:user_detail', user_id=user.id)
    
    context = {
        'target_user': user,
    }
    
    return render(request, 'admin/users/update.html', context)


@login_required
@superuser_only
@log_admin_activity('create', model_name='User')
def admin_add_user(request):
    """Ajouter un utilisateur"""
    if request.method == 'POST':
        # Récupérer les données du formulaire
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        roles = request.POST.getlist('role')
        
        try:
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=password
            )
            
            # Assigner les rôles
            if 'student' in roles:
                user.is_student = True
                StudentProfile.objects.create(user=user)
            
            if 'teacher' in roles:
                user.is_teacher = True
                TeacherProfile.objects.create(user=user)
            
            if 'staff' in roles:
                user.is_staff = True
            
            user.save()
            
            messages.success(request, f'Utilisateur {username} créé avec succès.')
            return redirect('admin:user_detail', user_id=user.id)
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return redirect('admin:users')


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('update', model_name='User')
def admin_user_deactivate(request, user_id):
    """Désactiver un utilisateur"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = False
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Utilisateur {user.username} désactivé'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('update', model_name='User')
def admin_user_activate(request, user_id):
    """Activer un utilisateur"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        user.is_active = True
        user.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Utilisateur {user.username} activé'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('delete', model_name='User')
def admin_user_delete(request, user_id):
    """Supprimer un utilisateur"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        # Ne pas permettre la suppression d'un superuser
        if user.is_superuser:
            return JsonResponse({
                'success': False,
                'error': 'Impossible de supprimer un superuser'
            })
        
        username = user.username
        user.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Utilisateur {username} supprimé'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
@admin_required(permission='manage_users')
@log_admin_activity('update', model_name='User')
def admin_user_revoke_premium(request, user_id):
    """Révoquer le statut premium d'un utilisateur"""
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        
        # Révoquer premium sur User
        user.is_premium = False
        user.premium_until = None
        user.save()
        
        # Révoquer premium sur StudentProfile si existe
        if hasattr(user, 'student_profile'):
            user.student_profile.is_premium = False
            user.student_profile.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Statut premium révoqué pour {user.username}'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


@login_required
@admin_required(permission='send_notifications')
@log_admin_activity('notification', model_name='User')
def admin_send_user_message(request):
    """Envoyer un message à un utilisateur"""
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        message_type = request.POST.get('message_type')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        user = get_object_or_404(User, id=user_id)
        
        # Ici, vous intégrerez votre système de notifications
        # Pour l'instant, on simule l'envoi
        print(f"Message envoyé à {user.email}: {subject}")
        print(f"Type: {message_type}")
        print(f"Message: {message}")
        
        return JsonResponse({
            'success': True,
            'message': 'Message envoyé avec succès'
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


# ======================
# GESTION DES ÉTUDIANTS
# ======================

@login_required
@admin_required(module='students')
def admin_students(request):
    """Liste des étudiants"""
    search_query = request.GET.get('q', '')
    level_filter = request.GET.get('level', '')
    status_filter = request.GET.get('status', '')
    premium_filter = request.GET.get('premium', '')
    
    students = StudentProfile.objects.select_related('user').all()
    
    # Filtres
    if search_query:
        students = students.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(institution__icontains=search_query) |
            Q(student_id_number__icontains=search_query)
        )
    
    if level_filter:
        students = students.filter(level=level_filter)
    
    if status_filter == 'active':
        students = students.filter(is_active_student=True)
    elif status_filter == 'inactive':
        students = students.filter(is_active_student=False)
    
    if premium_filter == 'premium':
        students = students.filter(is_premium=True)
    elif premium_filter == 'non_premium':
        students = students.filter(is_premium=False)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(students, 50)
    
    try:
        students_page = paginator.page(page)
    except PageNotAnInteger:
        students_page = paginator.page(1)
    except EmptyPage:
        students_page = paginator.page(paginator.num_pages)
    
    context = {
        'students': students_page,
        'search_query': search_query,
        'level_filter': level_filter,
        'status_filter': status_filter,
        'premium_filter': premium_filter,
        'total_count': students.count(),
        'level_choices': StudentProfile.LEVEL_CHOICES,
    }
    
    return render(request, 'admin/students/list.html', context)


# ======================
# GESTION DES ENSEIGNANTS
# ======================

@login_required
@admin_required(module='teachers')
def admin_teachers(request):
    """Liste des enseignants"""
    search_query = request.GET.get('q', '')
    verified_filter = request.GET.get('verified', '')
    active_filter = request.GET.get('active', '')
    accepting_filter = request.GET.get('accepting', '')
    
    teachers = TeacherProfile.objects.select_related('user').all()
    
    # Filtres
    if search_query:
        teachers = teachers.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(institution__icontains=search_query) |
            Q(title__icontains=search_query)
        )
    
    if verified_filter == 'verified':
        teachers = teachers.filter(is_verified=True)
    elif verified_filter == 'not_verified':
        teachers = teachers.filter(is_verified=False)
    
    if active_filter == 'active':
        teachers = teachers.filter(is_active_teacher=True)
    elif active_filter == 'inactive':
        teachers = teachers.filter(is_active_teacher=False)
    
    if accepting_filter == 'accepting':
        teachers = teachers.filter(is_accepting_new_students=True)
    elif accepting_filter == 'not_accepting':
        teachers = teachers.filter(is_accepting_new_students=False)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(teachers, 50)
    
    try:
        teachers_page = paginator.page(page)
    except PageNotAnInteger:
        teachers_page = paginator.page(1)
    except EmptyPage:
        teachers_page = paginator.page(paginator.num_pages)
    
    context = {
        'teachers': teachers_page,
        'search_query': search_query,
        'verified_filter': verified_filter,
        'active_filter': active_filter,
        'accepting_filter': accepting_filter,
        'total_count': teachers.count(),
    }
    
    return render(request, 'admin/teachers/list.html', context)


# ======================
# JOURNAUX D'ACTIVITÉ
# ======================

@login_required
@admin_required
def admin_activity_logs(request):
    """Journal des activités administratives"""
    activities = AdminActivityLog.objects.select_related('user').all()
    
    # Filtres
    user_filter = request.GET.get('user')
    action_filter = request.GET.get('action')
    model_filter = request.GET.get('model')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if user_filter:
        activities = activities.filter(user__username__icontains=user_filter)
    
    if action_filter:
        activities = activities.filter(action=action_filter)
    
    if model_filter:
        activities = activities.filter(model_name__icontains=model_filter)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(created_at__date__gte=date_from_obj)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(created_at__date__lte=date_to_obj)
        except ValueError:
            pass
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(activities, 100)
    
    try:
        activities_page = paginator.page(page)
    except PageNotAnInteger:
        activities_page = paginator.page(1)
    except EmptyPage:
        activities_page = paginator.page(paginator.num_pages)
    
    # Actions disponibles pour le filtre
    actions = AdminActivityLog.ACTION_CHOICES
    
    # Modèles uniques
    models = AdminActivityLog.objects.values_list('model_name', flat=True).distinct()
    
    context = {
        'activities': activities_page,
        'actions': actions,
        'models': models,
        'user_filter': user_filter,
        'action_filter': action_filter,
        'model_filter': model_filter,
        'date_from': date_from,
        'date_to': date_to,
        'total_count': activities.count(),
    }
    
    return render(request, 'admin/system/activity_logs.html', context)


@login_required
@superuser_only
def admin_activity_details(request, activity_id):
    """Détails d'une activité"""
    activity = get_object_or_404(AdminActivityLog, id=activity_id)
    
    return JsonResponse({
        'id': activity.id,
        'user': activity.user.username if activity.user else 'System',
        'action': activity.get_action_display(),
        'model_name': activity.model_name,
        'object_repr': activity.object_repr,
        'message': activity.message,
        'user_agent': activity.user_agent,
        'ip_address': activity.ip_address,
        'changes': activity.changes,
        'created_at': activity.created_at.isoformat(),
    })


@login_required
@superuser_only
def admin_export_activity_logs(request):
    """Exporter les journaux d'activité"""
    # Cette vue exporterait les logs en CSV ou JSON
    # Pour l'instant, on retourne un message
    return JsonResponse({
        'success': False,
        'message': 'Export non implémenté'
    })


@login_required
@superuser_only
def admin_clear_old_logs(request):
    """Supprimer les vieux logs"""
    if request.method == 'POST':
        # Supprimer les logs de plus de 90 jours
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count, _ = AdminActivityLog.objects.filter(
            created_at__lt=cutoff_date
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} logs supprimés',
            'deleted_count': deleted_count
        })
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})


# ======================
# NOTIFICATIONS
# ======================

@login_required
@admin_required(permission='send_notifications')
def admin_send_notification(request):
    """Envoyer une notification"""
    if request.method == 'POST':
        notification_type = request.POST.get('type')
        target = request.POST.get('target')
        message = request.POST.get('message')
        subject = request.POST.get('subject', 'Notification')
        urgent = request.POST.get('urgent') == 'on'
        
        # Déterminer les destinataires
        recipients = User.objects.all()
        
        if target == 'students':
            recipients = recipients.filter(is_student=True)
        elif target == 'teachers':
            recipients = recipients.filter(is_teacher=True)
        elif target == 'premium':
            recipients = recipients.filter(is_premium=True)
        elif target == 'staff':
            recipients = recipients.filter(is_staff=True)
        
        recipient_count = recipients.count()
        
        # Log de l'action
        AdminActivityLog.objects.create(
            user=request.user,
            action='notification',
            model_name='User',
            message=f'Notification envoyée à {recipient_count} utilisateurs: {subject}',
            changes={
                'type': notification_type,
                'target': target,
                'subject': subject,
                'urgent': urgent,
                'recipient_count': recipient_count
            }
        )
        
        messages.success(request, f"Notification envoyée à {recipient_count} utilisateurs!")
        return redirect('admin:dashboard')
    
    # Groupes cibles
    target_groups = [
        ('all', 'Tous les utilisateurs'),
        ('students', 'Étudiants uniquement'),
        ('teachers', 'Enseignants uniquement'),
        ('premium', 'Utilisateurs premium'),
        ('staff', 'Staff uniquement'),
    ]
    
    # Types de notifications
    notification_types = [
        ('email', 'Email'),
        ('in_app', 'Notification interne'),
        ('both', 'Email + Notification interne'),
    ]
    
    context = {
        'target_groups': target_groups,
        'notification_types': notification_types,
    }
    
    return render(request, 'admin/notifications/send.html', context)


@login_required
@admin_required
def admin_notification_stats(request):
    """Statistiques pour les notifications"""
    total_users = User.objects.count()
    total_students = User.objects.filter(is_student=True).count()
    total_teachers = User.objects.filter(is_teacher=True).count()
    total_premium = User.objects.filter(is_premium=True).count()
    
    return JsonResponse({
        'total_users': total_users,
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_premium': total_premium,
    })


# ======================
# STATISTIQUES ET API
# ======================

@login_required
@admin_required
def admin_quick_stats(request):
    """API pour les statistiques rapides (AJAX)"""
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Requête non autorisée'}, status=400)
    
    user = request.user
    stats_type = request.GET.get('type', 'general')
    
    data = {}
    
    if stats_type == 'general':
        # Statistiques générales
        if user.is_superuser or user.has_perm('users.view_users'):
            data['total_users'] = User.objects.count()
            data['new_users_today'] = User.objects.filter(
                date_joined__date=timezone.now().date()
            ).count()
        
        if user.is_superuser or user.has_perm('users.view_students'):
            data['total_students'] = StudentProfile.objects.count()
            data['premium_students'] = StudentProfile.objects.filter(
                is_premium=True
            ).count()
        
        if user.is_superuser or user.has_perm('users.view_teachers'):
            data['total_teachers'] = TeacherProfile.objects.count()
            data['verified_teachers'] = TeacherProfile.objects.filter(
                is_verified=True
            ).count()
    
    elif stats_type == 'financial':
        # Statistiques financières
        if user.is_superuser or user.has_perm('users.view_finance'):
            total_hourly_rate = TeacherProfile.objects.filter(
                hourly_rate__isnull=False
            ).aggregate(total=Sum('hourly_rate'))['total'] or 0
            
            data['total_hourly_rate'] = float(total_hourly_rate)
            data['active_teachers_with_rate'] = TeacherProfile.objects.filter(
                hourly_rate__isnull=False,
                is_active_teacher=True
            ).count()
    
    elif stats_type == 'academic':
        # Statistiques académiques
        if user.is_superuser or user.has_perm('users.view_enrollments'):
            data['total_enrollments'] = Enrollment.objects.count()
            data['active_enrollments'] = Enrollment.objects.filter(
                is_active=True
            ).count()
            
            # Par statut
            enrollment_status = Enrollment.objects.values('status').annotate(
                count=Count('id')
            )
            data['enrollment_by_status'] = {
                item['status']: item['count'] 
                for item in enrollment_status
            }
    
    return JsonResponse(data)


# ======================
# SYSTÈME (SUPERUSER ONLY)
# ======================

@login_required
@superuser_only
def admin_system_status(request):
    """Statut du système - uniquement pour superusers"""
    # Informations système
    from django.db import connection
    from django.conf import settings
    
    # Vérifier la connexion à la base de données
    db_status = 'OK'
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception as e:
        db_status = f'ERREUR: {str(e)}'
    
    # Statistiques de la base de données (adapté pour MySQL)
    table_sizes = []
    try:
        with connection.cursor() as cursor:
            # Pour MySQL, utiliser SHOW TABLE STATUS
            cursor.execute("SHOW TABLE STATUS")
            tables = cursor.fetchall()
            
            # Calculer la taille totale
            total_size = 0
            for table in tables:
                table_name = table[0]  # Nom de la table
                data_length = table[6] or 0  # Data_length
                index_length = table[8] or 0  # Index_length
                table_size = data_length + index_length
                total_size += table_size
                
                # Formater la taille
                size_str = format_bytes(table_size)
                table_sizes.append((table_name, size_str))
            
            # Trier par taille décroissante
            table_sizes.sort(key=lambda x: parse_bytes(x[1]), reverse=True)
    except Exception as e:
        table_sizes = [('Erreur', f'Impossible de récupérer les tailles: {str(e)}')]
    
    # Utilisation du disque
    disk_usage = psutil.disk_usage('/')
    
    # Mémoire
    memory = psutil.virtual_memory()
    
    # Logs récents d'erreur
    error_logs = []
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'django.log')
    
    if os.path.exists(log_file):
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                error_logs = [line for line in lines[-50:] if 'ERROR' in line or 'CRITICAL' in line]
        except Exception:
            error_logs = ['Impossible de lire le fichier de log']
    else:
        error_logs = ['Fichier de log non trouvé']
    
    context = {
        'db_status': db_status,
        'table_sizes': table_sizes,
        'disk_usage': {
            'total': disk_usage.total,
            'used': disk_usage.used,
            'free': disk_usage.free,
            'percent': disk_usage.percent
        },
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent
        },
        'error_logs': error_logs[-10:],  # 10 dernières erreurs
        'debug': settings.DEBUG,
        'timezone': settings.TIME_ZONE,
        'environment': settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else 'N/A',
        'database': connection.vendor,
    }
    
    return render(request, 'admin/system/status.html', context)


@login_required
@superuser_only
def admin_refresh_system_status(request):
    """Rafraîchir le statut système"""
    # Cette vue pourrait recalculer les statistiques
    return JsonResponse({
        'success': True,
        'message': 'Statut rafraîchi',
        'timestamp': timezone.now().isoformat()
    })


@login_required
@superuser_only
def admin_test_database(request):
    """Tester la connexion à la base de données"""
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            
            # Informations sur la base de données
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            return JsonResponse({
                'success': True,
                'message': 'Connexion à la base de données réussie',
                'version': version,
                'result': result[0]
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_database_info(request):
    """Informations détaillées sur la base de données MySQL"""
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            # Version MySQL
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            # Variables système
            cursor.execute("SHOW VARIABLES LIKE '%version%'")
            version_vars = cursor.fetchall()
            
            # Statut
            cursor.execute("SHOW STATUS")
            status = cursor.fetchall()
            
            # Processus en cours
            cursor.execute("SHOW PROCESSLIST")
            processes = cursor.fetchall()
            
            # Taille totale de la base de données
            cursor.execute("""
                SELECT table_schema AS 'Database',
                SUM(data_length + index_length) AS 'Size'
                FROM information_schema.TABLES
                WHERE table_schema = DATABASE()
                GROUP BY table_schema
            """)
            total_size = cursor.fetchone()
            
            return JsonResponse({
                'success': True,
                'version': version,
                'version_vars': dict(version_vars),
                'status': dict(status),
                'processes': len(processes),
                'total_size': total_size[1] if total_size else 0,
                'total_size_formatted': format_bytes(total_size[1]) if total_size else "0 B"
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_database_optimize(request, table_name=None):
    """Optimiser une table MySQL"""
    from django.db import connection
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        with connection.cursor() as cursor:
            if table_name:
                cursor.execute(f"OPTIMIZE TABLE `{table_name}`")
                result = cursor.fetchone()
                return JsonResponse({
                    'success': True,
                    'message': f'Table {table_name} optimisée',
                    'result': result
                })
            else:
                # Optimiser toutes les tables
                cursor.execute("SHOW TABLES")
                tables = [row[0] for row in cursor.fetchall()]
                
                results = []
                for table in tables:
                    cursor.execute(f"OPTIMIZE TABLE `{table}`")
                    results.append(cursor.fetchone())
                
                return JsonResponse({
                    'success': True,
                    'message': f'{len(tables)} tables optimisées',
                    'results': results
                })
                
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_database_backup(request):
    """Sauvegarde de la base de données MySQL"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    import subprocess
    import os
    from django.conf import settings
    from datetime import datetime
    
    try:
        # Configuration de la base de données
        db_settings = settings.DATABASES['default']
        
        # Chemin de sauvegarde
        backup_dir = os.path.join(settings.BASE_DIR, 'backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(backup_dir, f'backup_{timestamp}.sql')
        
        # Commande mysqldump
        cmd = [
            'mysqldump',
            f'--host={db_settings.get("HOST", "localhost")}',
            f'--port={db_settings.get("PORT", "3306")}',
            f'--user={db_settings["USER"]}',
            f'--password={db_settings["PASSWORD"]}',
            db_settings['NAME'],
            '--result-file', backup_file
        ]
        
        # Exécuter la commande
        cmd_str = ' '.join(cmd)
        result = subprocess.run(cmd_str, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            file_size = os.path.getsize(backup_file)
            return JsonResponse({
                'success': True,
                'message': f'Sauvegarde réussie: {backup_file}',
                'file': backup_file,
                'size': file_size,
                'size_formatted': format_bytes(file_size)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Erreur mysqldump: {result.stderr}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_cache_clear(request):
    """Vider le cache Django"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        from django.core.cache import cache
        cache.clear()
        
        # Nettoyer aussi le cache des sessions
        from django.contrib.sessions.models import Session
        Session.objects.all().delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Cache et sessions vidés avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_system_migrate(request):
    """Appliquer les migrations"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        # Exécuter les migrations
        result = subprocess.run(
            ['python', 'manage.py', 'migrate'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return JsonResponse({
                'success': True,
                'message': 'Migrations appliquées avec succès',
                'output': result.stdout
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Erreur migrations: {result.stderr}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_collect_static(request):
    """Collecter les fichiers statiques"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        # Collecter les fichiers statiques
        result = subprocess.run(
            ['python', 'manage.py', 'collectstatic', '--noinput'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return JsonResponse({
                'success': True,
                'message': 'Fichiers statiques collectés avec succès',
                'output': result.stdout
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Erreur collectstatic: {result.stderr}'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_system_restart(request):
    """Redémarrer l'application (simulation)"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        # Dans un environnement de production, vous redémarreriez le serveur
        # Pour le développement, on simule seulement
        
        # Vider le cache
        from django.core.cache import cache
        cache.clear()
        
        return JsonResponse({
            'success': True,
            'message': 'Application redémarrée (cache vidé)',
            'note': 'Dans un environnement de production, le serveur serait redémarré'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_toggle_maintenance(request):
    """Activer/désactiver le mode maintenance"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        data = json.loads(request.body)
        enabled = data.get('enabled', False)
        message = data.get('message', '')
        
        # Ici, vous implémenteriez votre logique de maintenance
        # Par exemple, créer/supprimer un fichier maintenance.txt
        
        maintenance_file = os.path.join(settings.BASE_DIR, 'maintenance.txt')
        
        if enabled:
            with open(maintenance_file, 'w') as f:
                f.write(message)
        else:
            if os.path.exists(maintenance_file):
                os.remove(maintenance_file)
        
        return JsonResponse({
            'success': True,
            'message': f'Mode maintenance {"activé" if enabled else "désactivé"}',
            'enabled': enabled
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@superuser_only
def admin_send_test_email(request):
    """Envoyer un email de test"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        from django.core.mail import send_mail
        
        send_mail(
            subject='Test email from MedZone Admin',
            message='Ceci est un email de test du système administratif.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=False,
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Email de test envoyé à {request.user.email}'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ======================
# GESTION DES PERMISSIONS
# ======================

@login_required
@superuser_only
def admin_permission_manager(request):
    """Gestionnaire de permissions - uniquement pour superusers"""
    from django.contrib.auth.models import Group
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'assign_permission_to_user':
            user_id = request.POST.get('user_id')
            permission_id = request.POST.get('permission_id')
            
            user = get_object_or_404(User, id=user_id)
            permission = get_object_or_404(AdminPermission, id=permission_id)
            
            permission.users.add(user)
            messages.success(request, f"Permission assignée à {user.username}")
        
        elif action == 'remove_permission_from_user':
            user_id = request.POST.get('user_id')
            permission_id = request.POST.get('permission_id')
            
            user = get_object_or_404(User, id=user_id)
            permission = get_object_or_404(AdminPermission, id=permission_id)
            
            permission.users.remove(user)
            messages.success(request, f"Permission retirée de {user.username}")
        
        elif action == 'assign_module_to_group':
            group_id = request.POST.get('group_id')
            module_id = request.POST.get('module_id')
            
            group = get_object_or_404(Group, id=group_id)
            module = get_object_or_404(AdminDashboardModule, id=module_id)
            
            module.groups.add(group)
            messages.success(request, f"Module assigné au groupe {group.name}")
        
        return redirect('admin:permission_manager')
    
    # Récupérer tous les utilisateurs staff
    staff_users = User.objects.filter(is_staff=True).order_by('username')
    
    # Récupérer tous les groupes
    groups = Group.objects.all().order_by('name')
    
    # Récupérer toutes les permissions administratives
    admin_permissions = AdminPermission.objects.all().order_by('name')
    
    # Récupérer tous les modules
    modules = AdminDashboardModule.objects.filter(is_active=True).order_by('order')
    
    # Statistiques
    total_staff = staff_users.count()
    total_groups = groups.count()
    total_permissions = admin_permissions.count()
    total_modules = modules.count()
    
    context = {
        'staff_users': staff_users,
        'groups': groups,
        'admin_permissions': admin_permissions,
        'modules': modules,
        'total_staff': total_staff,
        'total_groups': total_groups,
        'total_permissions': total_permissions,
        'total_modules': total_modules,
    }
    
    return render(request, 'admin/system/permissions.html', context)


@login_required
@superuser_only
def admin_create_group(request):
    """Créer un nouveau groupe"""
    if request.method == 'POST':
        from django.contrib.auth.models import Group, Permission
        
        name = request.POST.get('name')
        description = request.POST.get('description')
        permission_ids = request.POST.getlist('permissions')
        
        try:
            # Créer le groupe
            group = Group.objects.create(name=name)
            
            # Assigner les permissions Django standard
            permissions = Permission.objects.filter(id__in=permission_ids)
            group.permissions.set(permissions)
            
            messages.success(request, f'Groupe {name} créé avec succès')
            return redirect('admin:permission_manager')
            
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('admin:permission_manager')


@login_required
@superuser_only
def admin_refresh_permissions(request):
    """Rafraîchir les permissions"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})
    
    try:
        # Cette fonction pourrait synchroniser les permissions
        # Pour l'instant, on simule seulement
        
        return JsonResponse({
            'success': True,
            'message': 'Permissions rafraîchies',
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


# ======================
# FONCTIONS UTILITAIRES
# ======================

def format_bytes(size_in_bytes):
    """Formater les octets en unités lisibles"""
    if size_in_bytes is None:
        return "0 B"
    
    size = float(size_in_bytes)
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0 or unit == 'TB':
            return f"{size:.2f} {unit}"
        size /= 1024.0


def parse_bytes(size_str):
    """Parser une chaîne de taille en octets"""
    if not size_str:
        return 0
    
    try:
        size, unit = size_str.split()
        size = float(size)
        
        unit_map = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4,
        }
        
        return size * unit_map.get(unit.upper(), 1)
    except Exception:
        return 0


@login_required
@superuser_only
def admin_export_users(request):
    """Exporter les utilisateurs"""
    # Cette vue exporterait les utilisateurs en CSV ou Excel
    # Pour l'instant, on retourne un message
    return JsonResponse({
        'success': False,
        'message': 'Export non implémenté'
    })

