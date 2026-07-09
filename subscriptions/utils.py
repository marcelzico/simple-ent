# subscriptions/utils.py
from datetime import date
from .models import Subscription, SubscriptionUsageAudit
from django.core.exceptions import ValidationError
from django.utils import timezone


def get_remaining_attempts(subscription):
    """Get all remaining attempts for a subscription"""
    return {
        'mcq': subscription.get_remaining_mcq(),
        'mcq_exam': subscription.get_remaining_mcq_exams(),
        'qa': subscription.get_remaining_qa(),
        'qa_exam': subscription.get_remaining_qa_exams(),
        'tf': subscription.get_remaining_tf(),
    }





def get_student_active_subscription(user):
    """
    Get active subscription for a user's student profile
    """
    if not user.is_authenticated:
        return None
    
    if not hasattr(user, 'student_profile'):
        return None
    
    today = date.today()
    
    # Get approved subscription that is currently active
    try:
        subscription = Subscription.objects.filter(
            student=user.student_profile,
            payement_status='approved',
            start_date__lte=today,
            expires_at__gte=today
        ).order_by('-created_at').first()
        
        return subscription
    except Subscription.DoesNotExist:
        return None

def has_active_subscription(user):
    """Check if user has an active subscription"""
    subscription = get_student_active_subscription(user)
    return subscription is not None

def get_trial_days_remaining(user):
    """Get remaining days in trial period"""
    subscription = get_student_active_subscription(user)
    
    if not subscription:
        return 0
    
    # Check if it's a trial subscription (price 0 and specific feature)
    if subscription.feature and subscription.feature.price == 0:
        today = date.today()
        if today <= subscription.expires_at:
            return (subscription.expires_at - today).days
    
    return 0

def is_trial_subscription(user):
    """Check if user's active subscription is a trial"""
    subscription = get_student_active_subscription(user)
    
    if subscription and subscription.feature:
        return subscription.feature.price == 0 or subscription.feature.code == 'TRIAL_30DAYS'
    
    return False

def can_access_feature(user, feature_code):
    """
    Check if user can access a specific feature
    feature_code can be: 'mcq', 'qa', 'tf', 'mcq_exam', 'qa_exam', 
    'can_add_resume', 'can_add_notes', etc.
    """
    subscription = get_student_active_subscription(user)
    
    if not subscription:
        return False
    
    # Map feature codes to check methods
    if feature_code == 'mcq':
        return subscription.get_remaining_mcq() > 0
    elif feature_code == 'qa':
        return subscription.get_remaining_qa() > 0
    elif feature_code == 'tf':
        return subscription.get_remaining_tf() > 0
    elif feature_code == 'mcq_exam':
        return subscription.get_remaining_mcq_exams() > 0
    elif feature_code == 'qa_exam':
        return subscription.get_remaining_qa_exams() > 0
    else:
        # Check boolean features
        return subscription.is_feature_available(feature_code)

def record_quiz_attempt(user, quiz_type):
    """
    Record a quiz attempt for the user
    quiz_type: 'mcq', 'qa', 'tf', 'mcq_exam', 'qa_exam'
    """
    subscription = get_student_active_subscription(user)
    
    if not subscription:
        raise ValidationError("No active subscription found")
    
    # Record attempt based on quiz type
    if quiz_type == 'mcq':
        subscription.record_mcq_attempt()
    elif quiz_type == 'qa':
        subscription.record_qa_attempt()
    elif quiz_type == 'tf':
        subscription.record_tf_attempt()
    elif quiz_type == 'mcq_exam':
        subscription.record_mcq_exam_attempt()
    elif quiz_type == 'qa_exam':
        subscription.record_qa_exam_attempt()
    else:
        raise ValidationError(f"Unknown quiz type: {quiz_type}")
    
    # Log the attempt
    SubscriptionUsageAudit.log_usage(
        action_type='quiz_complete',
        details={'quiz_type': quiz_type},
        subscription=subscription,
        student=subscription.student
    )
    
    return True

def get_remaining_attempts(user, quiz_type):
    """Get remaining attempts for a specific quiz type"""
    subscription = get_student_active_subscription(user)
    
    if not subscription:
        return 0
    
    if quiz_type == 'mcq':
        return subscription.get_remaining_mcq()
    elif quiz_type == 'qa':
        return subscription.get_remaining_qa()
    elif quiz_type == 'tf':
        return subscription.get_remaining_tf()
    elif quiz_type == 'mcq_exam':
        return subscription.get_remaining_mcq_exams()
    elif quiz_type == 'qa_exam':
        return subscription.get_remaining_qa_exams()
    
    return 0