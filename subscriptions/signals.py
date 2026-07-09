# subscriptions/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from utilisateur.models import User
from student.models import StudentProfile
from .models import Subscription, Feature, SubscriptionUsageAudit

@receiver(post_save, sender=User)
def create_trial_subscription_for_new_user(sender, instance, created, **kwargs):
    """
    Automatically create an approved trial subscription for new users
    who have a student profile
    """
    if created:
        # Check if user has a student profile (created via post_save signal from student app)
        # We need to wait a bit for the student profile to be created
        from django.db import transaction
        from django.core.management import call_command
        
        def create_trial():
            # Give time for student profile to be created
            try:
                # Check if user has student profile
                if hasattr(instance, 'student_profile'):
                    student_profile = instance.student_profile
                    create_trial_subscription(student_profile, instance)
                else:
                    # If student profile doesn't exist yet, schedule creation
                    # This handles the case where student profile is created after user
                    pass
            except Exception as e:
                print(f"Error creating trial subscription for {instance.email}: {e}")
        
        # Use transaction.on_commit to ensure user is fully saved
        transaction.on_commit(create_trial)

@receiver(post_save, sender=StudentProfile)
def create_trial_subscription_for_student_profile(sender, instance, created, **kwargs):
    """
    Auto-create trial subscription when a StudentProfile is created
    This is more reliable than using User signal
    """
    if created:
        create_trial_subscription(instance, instance.user)

def create_trial_subscription(student_profile, user):
    """
    Helper function to create trial subscription for a student
    """
    # Check if student already has any subscription (active or pending)
    existing_sub = Subscription.objects.filter(
        student=student_profile
    ).exclude(payement_status='rejected').first()
    
    if existing_sub:
        # Student already has a subscription, don't create trial
        print(f"Student {user.email} already has subscription {existing_sub.id}")
        return
    
    # Get the trial feature
    try:
        trial_feature = Feature.objects.get(code='TRIAL_30DAYS')
    except Feature.DoesNotExist:
        print("Trial feature not found! Please create it first.")
        # Create trial feature on the fly if not exists (fallback)
        trial_feature = Feature.objects.create(
            code='TRIAL_30DAYS',
            name='Trial Period - 30 Days',
            mcq_features=50,
            mcq_exam_feature=10,
            qa_features=50,
            qa_exam_feature=10,
            tf_features=50,
            validity_day_number=30,
            can_add_resume=True,
            can_add_notes=True,
            can_view_terminology=True,
            can_practice_terminology=True,
            can_view_public_flashcard=True,
            can_practice_quizlet_learning_mode=True,
            can_view_image_quiz=True,
            can_practice_image_quiz=True,
            can_ask_question=True,
            can_view_dicussion=True,
            can_add_own_terminology=True,
            can_add_own_flashcard=True,
            price=0,
        )
    
    # Calculate dates
    start_date = date.today()
    expires_at = start_date + timedelta(days=trial_feature.validity_day_number)
    
    # Create the subscription - directly approved (bypass payment)
    subscription = Subscription.objects.create(
        student=student_profile,
        feature=trial_feature,
        amount=0,  # Free trial
        payment=None,  # No payment required
        planning_date_to_start=start_date,
        start_date=start_date,
        expires_at=expires_at,
        payement_status='approved',  # Directly approved
        description=f"Auto-created 30-day trial subscription for {user.email}",
        approved_by=None,  # System auto-approved
        approved_at=timezone.now(),
    )
    
    # Log the auto-creation
    SubscriptionUsageAudit.log_usage(
        action_type='subscription_created',
        details={
            'auto_created': True,
            'trial': True,
            'feature': trial_feature.code,
            'expires_at': expires_at.isoformat()
        },
        subscription=subscription,
        student=student_profile
    )
    
    print(f"✅ Auto-created trial subscription for {user.email} (expires: {expires_at})")
    
    return subscription


