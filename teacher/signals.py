from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import NotificationPreference, TeacherDashboardWidget


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_teacher_defaults(sender, instance, created, **kwargs):
    """
    Crée les préférences par défaut et les widgets dashboard lorsqu'un utilisateur
    devient enseignant
    """
    if not instance.is_teacher:
        return
    
    # Créer les préférences de notification par défaut
    notification_types = [choice[0] for choice in NotificationPreference.NOTIFICATION_TYPES]
    
    for notif_type in notification_types:
        NotificationPreference.objects.get_or_create(
            teacher=instance,
            notification_type=notif_type,
            defaults={
                'is_enabled': True,
                'send_email': True,
                'send_sms': False,
            }
        )
    
    # Créer les widgets dashboard par défaut
    default_widgets = [
        ('stats', 1),
        ('chart_performance', 2),
        ('chart_completion', 3),
        ('chart_scores', 4),
        ('recent_activity', 5),
        ('top_students', 6),
        ('struggling_students', 7),
    ]
    
    for widget_type, order in default_widgets:
        TeacherDashboardWidget.objects.get_or_create(
            teacher=instance,
            widget_type=widget_type,
            defaults={
                'order': order,
                'is_visible': True,
            }
        )

