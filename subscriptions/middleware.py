# # subscriptions/middleware.py
# from django.shortcuts import redirect
# from django.urls import reverse
# from django.contrib import messages
# from django.utils.deprecation import MiddlewareMixin
# from .utils import get_student_active_subscription, get_trial_days_remaining, is_trial_subscription

# class SubscriptionMiddleware(MiddlewareMixin):
#     """
#     Middleware to check subscription status and show trial expiration warnings
#     """
    
#     def process_view(self, request, view_func, view_args, view_kwargs):
#         # Skip for admin, login, register, and public pages
#         exempt_urls = [
#             '/admin/',
#             '/accounts/login/',
#             '/accounts/register/',
#             '/accounts/logout/',
#             '/subscriptions/expired/',
#             '/subscriptions/upgrade/',
#         ]
        
#         current_path = request.path
        
#         for url in exempt_urls:
#             if current_path.startswith(url):
#                 return None
        
#         # Check if user is authenticated and has student profile
#         if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
#             subscription = get_student_active_subscription(request.user)
            
#             if not subscription:
#                 # No active subscription
#                 messages.warning(
#                     request, 
#                     "Your subscription has expired. Please upgrade to continue accessing content."
#                 )
#                 return redirect('student:dashboard')
            
#             # Show warning for trial users whose trial is ending soon
#             if is_trial_subscription(request.user):
#                 days_left = get_trial_days_remaining(request.user)
                
#                 if days_left <= 3 and days_left > 0:
#                     messages.warning(
#                         request,
#                         f"⚠️ Your free trial ends in {days_left} days! "
#                         f"Subscribe now to continue uninterrupted access."
#                     )
#                 elif days_left == 1:
#                     messages.warning(
#                         request,
#                         "⚠️ Your free trial ends TOMORROW! Don't lose access - upgrade today."
#                     )
        
#         return None



# subscriptions/middleware.py
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from .utils import get_student_active_subscription, get_trial_days_remaining, is_trial_subscription

class SubscriptionMiddleware(MiddlewareMixin):
    """
    Middleware to check subscription status and show trial expiration warnings
    """
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for admin, login, register, and ALL subscription-related pages
        exempt_urls = [
            '/admin/',
            '/login/',
            '/register/',
            '/logout/',
            '/subscriptions/expired/',
            '/subscriptions/upgrade/',
            '/subscription/subscription/create/',  # ADD THIS
            '/subscription/',  # ADD THIS - catches all subscription URLs
            '/student/dashboard/',  # ADD THIS if dashboard has its own check
        ]
        
        current_path = request.path
        
        for url in exempt_urls:
            if current_path.startswith(url):
                return None
        
        # Check if user is authenticated and has student profile
        if request.user.is_authenticated and hasattr(request.user, 'student_profile'):
            subscription = get_student_active_subscription(request.user)
            
            if not subscription:
                # Don't show message on every redirect - use session flag
                if not request.session.get('subscription_redirect_notified', False):
                    messages.warning(
                        request, 
                        "Your subscription has expired. Please upgrade to continue accessing content."
                    )
                    request.session['subscription_redirect_notified'] = True
                
                return redirect('subscriptions:student_dashboard')
            
            # Clear the notification flag if subscription exists
            if 'subscription_redirect_notified' in request.session:
                del request.session['subscription_redirect_notified']
            
            # Show warning for trial users whose trial is ending soon
            if is_trial_subscription(request.user):
                days_left = get_trial_days_remaining(request.user)
                
                if days_left <= 3 and days_left > 0:
                    messages.warning(
                        request,
                        f"⚠️ Your free trial ends in {days_left} days! "
                        f"Subscribe now to continue uninterrupted access."
                    )
                elif days_left == 1:
                    messages.warning(
                        request,
                        "⚠️ Your free trial ends TOMORROW! Don't lose access - upgrade today."
                    )
        
        return None
