from django.db import models
from utilisateur.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# Create your models here.

class TeacherProfile(models.Model):
    """
    Informations spécifiques aux enseignants
    """
    TITRE_CHOICES = [
        ('Dr', 'Docteur'),
        ('Pr', 'Professeur'),
        ('M.', 'Monsieur'),
        ('Mme', 'Madame'),
        ('Mlle', 'Mademoiselle'),
    ]
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        verbose_name="Utilisateur"
    )
    
    titre = models.CharField(
        max_length=10,
        choices=TITRE_CHOICES,
        blank=True,
        null=True,
        verbose_name="Titre"
    )
    
    specialite = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Spécialité"
    )
    
    bio = models.TextField(
        blank=True,
        null=True,
        verbose_name="Biographie professionnelle",
        help_text="Parcours, domaines d'expertise, etc."
    )
    
    bureau = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Bureau/Local"
    )
    
    heures_consultation = models.TextField(
        blank=True,
        null=True,
        verbose_name="Heures de consultation",
        help_text="Ex: Lundi 14h-16h, Mercredi 10h-12h"
    )
    
    phone_pro = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Téléphone professionnel"
    )
    
    photo = models.ImageField(
        upload_to='teacher_photos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Photo de profil"
    )
    
    date_embauche = models.DateField(
        blank=True,
        null=True,
        verbose_name="Date d'embauche"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        titre_aff = f"{self.titre} " if self.titre else ""
        return f"{titre_aff}{self.user.get_full_name() or self.user.username}"
    
    @property
    def full_title(self):
        """Retourne le titre complet pour l'affichage"""
        return f"{self.titre or ''} {self.user.get_full_name() or self.user.username}".strip()
    
    class Meta:
        db_table = 'teacher_profiles'
        verbose_name = "Profil enseignant"
        verbose_name_plural = "Profils enseignants"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['specialite']),
        ]


class NotificationPreference(models.Model):
    """
    Préférences de notifications pour les enseignants
    """
    NOTIFICATION_TYPES = [
        ('quiz_completed', 'Quiz complété par un étudiant'),
        ('low_score', 'Score faible (< 50%)'),
        ('high_score', 'Score excellent (> 90%)'),
        ('new_question', 'Nouvelle question posée'),
        ('daily_summary', 'Résumé quotidien'),
        ('weekly_report', 'Rapport hebdomadaire'),
    ]
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_prefs',
        verbose_name="Enseignant"
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPES,
        verbose_name="Type de notification"
    )
    
    is_enabled = models.BooleanField(
        default=True,
        verbose_name="Activé"
    )
    
    send_email = models.BooleanField(
        default=True,
        verbose_name="Envoyer par email"
    )
    
    send_sms = models.BooleanField(
        default=False,
        verbose_name="Envoyer par SMS"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notifications"
        unique_together = ['teacher', 'notification_type']
    
    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{self.teacher.get_full_name()} - {self.get_notification_type_display()} {status}"

 
class TeacherDashboardWidget(models.Model):
    """
    Configuration des widgets du dashboard pour chaque enseignant
    """
    WIDGET_TYPES = [
        ('stats', 'Statistiques générales'),
        ('chart_performance', 'Graphique de performance'),
        ('chart_completion', 'Taux de complétion'),
        ('chart_scores', 'Distribution des notes'),
        ('recent_activity', 'Activité récente'),
        ('top_students', 'Meilleurs étudiants'),
        ('struggling_students', 'Étudiants en difficulté'),
        ('upcoming_quizzes', 'Quiz à venir'),
    ]
    
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets',
        verbose_name="Enseignant"
    )
    
    widget_type = models.CharField(
        max_length=50,
        choices=WIDGET_TYPES,
        verbose_name="Type de widget"
    )
    
    order = models.IntegerField(
        default=0,
        verbose_name="Ordre d'affichage"
    )
    
    is_visible = models.BooleanField(
        default=True,
        verbose_name="Visible"
    )
    
    class Meta:
        verbose_name = "Widget du tableau de bord"
        verbose_name_plural = "Widgets du tableau de bord"
        ordering = ['teacher', 'order']
        unique_together = ['teacher', 'widget_type']
    
    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.get_widget_type_display()}"