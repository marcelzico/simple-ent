from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction

from student.models import StudentProfile

User = get_user_model()

@receiver(post_save, sender=User)
def handle_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create student profile when user is created
    """
    if created and instance.is_student:
        try:
            with transaction.atomic():
                # Create StudentProfile if it doesn't exist
                StudentProfile.objects.get_or_create(user=instance)
                print(f"Created StudentProfile for new student user: {instance.email}")
        except Exception as e:
            print(f"Error creating StudentProfile: {e}")
    elif not created and instance.is_student:
        # Handle case where user becomes a student after creation
        if not hasattr(instance, 'student_profile'):
            try:
                with transaction.atomic():
                    StudentProfile.objects.create(user=instance)
                    print(f"Created StudentProfile for existing user: {instance.email}")
            except Exception as e:
                print(f"Error creating StudentProfile for existing user: {e}")