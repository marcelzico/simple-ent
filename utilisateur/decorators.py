# users/decorators.py - NOUVEAU FICHIER
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import user_passes_test
from functools import wraps
import json

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError

def admin_required(view_func=None, permission=None, module=None):
    """
    Décorateur pour les vues administratives
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Vérifier si l'utilisateur est authentifié
            if not request.user.is_authenticated:
                from django.contrib.auth.views import redirect_to_login
                return redirect_to_login(request.get_full_path())
            
            # Superuser a accès à tout
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Staff requis
            if not request.user.is_staff:
                raise PermissionDenied("Accès réservé au personnel administratif.")
            
            # Vérifier la permission spécifique
            if permission:
                if not request.user.has_perm(permission) and permission not in request.user.admin_permissions.values_list('codename', flat=True):
                    raise PermissionDenied(f"Permission '{permission}' requise.")
            
            # Vérifier l'accès au module
            if module:
                from .models import AdminDashboardModule
                try:
                    dashboard_module = AdminDashboardModule.objects.get(codename=module)
                    if not dashboard_module.user_has_access(request.user):
                        raise PermissionDenied(f"Accès au module '{module}' non autorisé.")
                except AdminDashboardModule.DoesNotExist:
                    pass
            
            return view_func(request, *args, **kwargs)
        
        return _wrapped_view
    
    if view_func:
        return decorator(view_func)
    return decorator


def staff_only(view_func):
    """Décorateur pour les vues réservées au staff"""
    def check_staff(user):
        return user.is_authenticated and user.is_staff
    
    return user_passes_test(check_staff)(view_func)


def superuser_only(view_func):
    """Décorateur pour les vues réservées aux superusers"""
    def check_superuser(user):
        return user.is_authenticated and user.is_superuser
    
    return user_passes_test(check_superuser)(view_func)


def log_admin_activity(action, model_name=None, object_id=None, object_repr=None, changes=None):
    """
    Décorateur pour journaliser les activités administratives
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            from .models import AdminActivityLog
            
            # Exécuter la vue
            response = view_func(request, *args, **kwargs)
            
            # Journaliser l'activité
            if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
                log_entry = AdminActivityLog(
                    user=request.user,
                    action=action,
                    model_name=model_name or view_func.__name__,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                    message=f"{action} via {view_func.__name__}"
                )
                
                # Ajouter des détails supplémentaires
                if object_id:
                    log_entry.object_id = str(object_id)
                
                if object_repr:
                    log_entry.object_repr = str(object_repr)[:200]
                
                if changes:
                    log_entry.changes = changes
                
                log_entry.save()
            
            return response
        
        return _wrapped_view
    
    return decorator


"""
Reusable decorators for subscription-based access control.
Place this file inside the 'subscriptions' app.
"""



def student_required(view_func):
    """
    Ensures the user is authenticated and flagged as student.
    Allows superusers to bypass.
    Redirects otherwise.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Allow superusers
        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        if not hasattr(request.user, 'student_profile') or not request.user.student_profile:
            messages.error(request, "Cette section est réservée aux étudiants.")
            return redirect('utilisateur:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def non_student_required(view_func):
    """
    Ensures the user is authenticated and is a staff member (Django staff) or superuser.
    For Django admin access control.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        if not (request.user.is_staff or request.user.is_superuser or request.user.is_teacher):
            messages.error(request, "Cette section est réservée au personnel administratif.")
            return redirect('utilisateur:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ----------------------------
# 2. Student or Superuser (no regular staff)
# ----------------------------
def student_or_superuser_required(view_func):
    """
    Allows students and superusers only.
    Regular staff members are NOT allowed.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Allow superusers immediately
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        # Check for student profile
        if not hasattr(request.user, 'student_profile') or not request.user.student_profile:
            # If user is staff (but not superuser), reject
            if request.user.is_staff:
                messages.error(request, "Cette section est réservée aux étudiants et administrateurs principaux.")
                return redirect('utilisateur:dashboard')
            
            messages.error(request, "Cette section est réservée aux étudiants.")
            return redirect('utilisateur:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ----------------------------
# 3. Staff or Superuser (no regular students)
# ----------------------------
def staff_or_superuser_required(view_func):
    """
    Allows staff members and superusers only.
    Regular students are NOT allowed.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Allow staff or superuser
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Cette section est réservée au personnel administratif.")
        return redirect('utilisateur:dashboard')
    return _wrapped_view


# ----------------------------
# 4. Superuser only
# ----------------------------
def superuser_only_required(view_func):
    """
    Allows superusers only.
    Staff members and students are NOT allowed.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        if not request.user.is_superuser:
            messages.error(request, "Cette section est réservée aux administrateurs principaux.")
            return redirect('utilisateur:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ============================================================================
# CLASS-BASED VIEW DECORATORS (as method decorators)
# ============================================================================

def student_only_required():
    """
    Method decorator for class-based views.
    Allows students ONLY (no superuser/staff).
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(self, request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
                return redirect('utilisateur:login')

            # Explicitly reject superusers and staff
            if request.user.is_superuser or request.user.is_staff:
                messages.error(request, "Cette section est réservée exclusivement aux étudiants.")
                return redirect('utilisateur:dashboard')

            if not hasattr(request.user, 'student_profile') or not request.user.student_profile:
                messages.error(request, "Cette section est réservée aux étudiants.")
                return redirect('utilisateur:dashboard')

            return view_func(self, request, *args, **kwargs)
        return wrapped
    return decorator


# ============================================================================
# MIXINS FOR CLASS-BASED VIEWS
# ============================================================================

class StudentOnlyMixin:
    """Mixin for class-based views that require student users ONLY"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Explicitly reject superusers and staff
        if request.user.is_superuser or request.user.is_staff:
            messages.error(request, "Cette section est réservée exclusivement aux étudiants.")
            return redirect('utilisateur:dashboard')

        if not hasattr(request.user, 'student_profile') or not request.user.student_profile:
            messages.error(request, "Cette section est réservée aux étudiants.")
            return redirect('utilisateur:dashboard')

        return super().dispatch(request, *args, **kwargs)


class StudentOrSuperuserMixin:
    """Mixin for class-based views that allow students and superusers only"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Allow superusers immediately
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # Check for student profile
        if not hasattr(request.user, 'student_profile') or not request.user.student_profile:
            # If user is staff (but not superuser), reject
            if request.user.is_staff:
                messages.error(request, "Cette section est réservée aux étudiants et administrateurs principaux.")
                return redirect('utilisateur:dashboard')
            
            messages.error(request, "Cette section est réservée aux étudiants.")
            return redirect('utilisateur:dashboard')

        return super().dispatch(request, *args, **kwargs)


class StaffOrSuperuserMixin:
    """Mixin for class-based views that require staff or superuser"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        # Allow staff or superuser
        if request.user.is_staff or request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        messages.error(request, "Cette section est réservée au personnel administratif.")
        return redirect('utilisateur:dashboard')


class SuperuserOnlyMixin:
    """Mixin for class-based views that require superuser ONLY"""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.info(request, "Veuillez vous connecter pour accéder à cette section.")
            return redirect('utilisateur:login')

        if not request.user.is_superuser:
            messages.error(request, "Cette section est réservée aux administrateurs principaux.")
            return redirect('utilisateur:dashboard')

        return super().dispatch(request, *args, **kwargs)

