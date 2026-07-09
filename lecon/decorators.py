from django.core.exceptions import PermissionDenied
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from subscriptions.models import Subscription, SubscriptionUsageAudit
from django.http import HttpResponseForbidden


def superuser_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponseForbidden("Vous n'avez pas accès à cette page.")
        return view_func(request, *args, **kwargs)
    return wrapper


def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect('login')
            
        if not (request.user.is_superuser or request.user.is_teacher):
            raise PermissionDenied()
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def subscription_required(feature=None):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated or not request.user.is_student:
                messages.error(request, "Accès réservé aux étudiants.")
                return redirect('utilisateur:login')  # Or dashboard

            student_profile = request.user.student_profile
            active_sub = Subscription.get_student_active_subscription(student_profile)
            if not active_sub:
                messages.warning(request, "Abonnement requis pour accéder à cette fonctionnalité.")
                return redirect('subscriptions:subscribe')  # Your subscription page

            if feature and not hasattr(active_sub.feature, feature) or not getattr(active_sub.feature, feature):
                messages.error(request, "Cette fonctionnalité n'est pas disponible dans votre abonnement.")
                return redirect('utilisateur:dashboard')

            # Log access if needed
            SubscriptionUsageAudit.log_usage(
                action_type='feature_access',
                details={'feature': feature},
                request=request,
                subscription=active_sub,
                student=student_profile
            )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator