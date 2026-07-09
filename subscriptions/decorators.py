"""
Reusable decorators for subscription-based access control.
Place this file inside the 'subscriptions' app.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.decorators import method_decorator
from .models import Subscription, SubscriptionUsageAudit
from django.core.exceptions import ValidationError


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

        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Cette section est réservée au personnel administratif.")
            return redirect('utilisateur:dashboard')

        return view_func(request, *args, **kwargs)
    return _wrapped_view


def active_subscription_required(view_func=None, *, feature=None, message=None):
    """
    Main decorator — checks for an active approved subscription.
    
    Optional:
      - feature: string name of the Feature flag to check (e.g. 'can_add_notes')
      - message: custom error message when feature is missing
    
    Usage examples:
    
    @active_subscription_required
    def basic_view(request): ...

    @active_subscription_required(feature='can_add_resume')
    def add_resume_view(request): ...

    @active_subscription_required(feature='can_practice_quizlet_learning_mode', message="Quiz en mode apprentissage réservé aux abonnés Pro")
    def start_quiz_learning_mode(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        @student_required
        def wrapper(request, *args, **kwargs):
            # Allow superusers to bypass subscription checks
            if request.user.is_staff:
                return view_func(request, *args, **kwargs)
                
            try:
                profile = request.user.student_profile
            except AttributeError:
                messages.error(request, "Profil étudiant introuvable. Contactez le support.")
                return redirect('utilisateur:dashboard')
 
            active_subscription = Subscription.get_student_active_subscription(profile)

            if not active_subscription:
                messages.warning(request, "Vous devez souscrire à un abonnement actif pour accéder à ce contenu.")
                return redirect('subscriptions:create_subscription')
            
            # FIX: Check if feature exists on the subscription
            if not active_subscription.feature:
                messages.error(request, "Votre abonnement n'a pas de forfait associé. Contactez le support.")
                return redirect('utilisateur:dashboard')

            # Optional feature flag check
            if feature:
                # FIX: Use getattr with default False for safer checking
                feature_value = getattr(active_subscription.feature, feature, False)
                
                if not feature_value:
                    msg = message or f"Cette fonctionnalité nécessite un abonnement avec l'option « {feature} »."
                    messages.error(request, msg)
                    return redirect('utilisateur:dashboard')

                # Log feature usage (optional but recommended for analytics)
                SubscriptionUsageAudit.log_usage(
                    action_type='feature_access',
                    details={
                        'feature': feature,
                        'view': view_func.__name__,
                        'url': request.path,
                    },
                    request=request,
                    subscription=active_subscription,
                    student=profile
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    # Allow usage with or without parentheses
    if view_func is None:
        return decorator
    return decorator(view_func)


# ───────────────────────────────────────────────
#   Class-based view decorator helpers
# ────────────────────────────────────────────────

def check_quiz_access(view_func=None, *, quiz_type, increment_usage=True):
    """
    Decorator to check if student has access to specific quiz type
    and optionally increment usage.
    
    quiz_type: 'mcq', 'mcq_exam', 'qa', 'qa_exam', 'tf'
    increment_usage: Whether to increment the usage counter
    """
    def decorator(view_func):
        @wraps(view_func)
        @active_subscription_required
        def wrapper(request, *args, **kwargs):
            # Allow superusers to bypass quiz access checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
                
            student = request.user.student_profile
            active_subscription = Subscription.get_student_active_subscription(student)
            
            if not active_subscription:
                messages.error(request, "No active subscription found.")
                return redirect('subscriptions:student_dashboard')
            
            # Map quiz types to subscription methods
            quiz_methods = {
                'mcq': 'record_mcq_attempt',
                'mcq_exam': 'record_mcq_exam_attempt',
                'qa': 'record_qa_attempt',
                'qa_exam': 'record_qa_exam_attempt',
                'tf': 'record_tf_attempt',
            }
            
            if quiz_type not in quiz_methods:
                messages.error(request, f"Invalid quiz type: {quiz_type}")
                return redirect('subscriptions:student_dashboard')
            
            # Check if subscription has access to this quiz type
            method_name = quiz_methods[quiz_type]
            
            if increment_usage:
                try:
                    # Record the attempt
                    getattr(active_subscription, method_name)()
                    
                    # Log the usage
                    SubscriptionUsageAudit.log_usage(
                        action_type=f'{quiz_type}_attempt',
                        details={
                            'quiz_type': quiz_type,
                            'view': view_func.__name__,
                        },
                        request=request,
                        subscription=active_subscription,
                        student=student
                    )
                    
                    messages.info(request, f"{quiz_type.upper()} attempt recorded. Remaining: {getattr(active_subscription, f'get_remaining_{quiz_type}')()}")
                    
                except ValidationError as e:
                    messages.error(request, str(e))
                    return redirect('subscriptions:student_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    if view_func is None:
        return decorator
    return decorator(view_func)


def method_active_subscription_required(feature=None, message=None):
    """
    Correct method decorator for class-based views.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(self, request, *args, **kwargs):
            # Allow superusers to bypass
            if request.user.is_staff:
                return view_func(self, request, *args, **kwargs)
                
            try:
                profile = request.user.student_profile
            except AttributeError:
                messages.error(request, "Profil étudiant introuvable. Contactez le support.")
                return redirect('utilisateur:dashboard')

            active_subscription = Subscription.get_student_active_subscription(profile)

            if not active_subscription:
                messages.warning(request, "Vous devez souscrire à un abonnement actif pour accéder à ce contenu.")
                return redirect('subscriptions:create_subscription')
            
            # FIX: Check if feature exists on the subscription
            if not active_subscription.feature:
                messages.error(request, "Votre abonnement n'a pas de forfait associé. Contactez le support.")
                return redirect('utilisateur:dashboard')

            # Optional feature flag check
            if feature:
                # FIX: Use getattr with default False for safer checking
                feature_value = getattr(active_subscription.feature, feature, False)
                
                if not feature_value:
                    msg = message or f"Cette fonctionnalité nécessite un abonnement avec l'option « {feature} »."
                    messages.error(request, msg)
                    return redirect('utilisateur:dashboard')

                # Log feature usage
                SubscriptionUsageAudit.log_usage(
                    action_type='feature_access',
                    details={
                        'feature': feature,
                        'view': view_func.__name__,
                        'url': request.path,
                    },
                    request=request,
                    subscription=active_subscription,
                    student=profile
                )

            return view_func(self, request, *args, **kwargs)
        return wrapped
    return decorator


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


class ActiveSubscriptionRequiredMixin:
    """Mixin for class-based views that require active subscription"""
    feature = None
    message = None
    
    def dispatch(self, request, *args, **kwargs):
        # Allow superusers to bypass
        if request.user.is_staff:
            return super().dispatch(request, *args, **kwargs)
            
        try:
            profile = request.user.student_profile
        except AttributeError:
            messages.error(request, "Profil étudiant introuvable. Contactez le support.")
            return redirect('utilisateur:dashboard')

        active_subscription = Subscription.get_student_active_subscription(profile)

        if not active_subscription:
            messages.warning(request, "Vous devez souscrire à un abonnement actif pour accéder à ce contenu.")
            return redirect('subscriptions:create_subscription')
        
        # FIX: Check if feature exists on the subscription
        if not active_subscription.feature:
            messages.error(request, "Votre abonnement n'a pas de forfait associé. Contactez le support.")
            return redirect('utilisateur:dashboard')

        # Optional feature flag check
        if self.feature:
            # FIX: Use getattr with default False for safer checking
            feature_value = getattr(active_subscription.feature, self.feature, False)
            
            if not feature_value:
                msg = self.message or f"Cette fonctionnalité nécessite un abonnement avec l'option « {self.feature} »."
                messages.error(request, msg)
                return redirect('utilisateur:dashboard')

            # Log feature usage
            SubscriptionUsageAudit.log_usage(
                action_type='feature_access',
                details={
                    'feature': self.feature,
                    'view': self.__class__.__name__,
                    'url': request.path,
                },
                request=request,
                subscription=active_subscription,
                student=profile
            )

        return super().dispatch(request, *args, **kwargs)
    
    