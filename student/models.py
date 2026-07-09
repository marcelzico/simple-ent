from django.db import models
from datetime import timedelta
from decimal import Decimal
from utilisateur.models import User
from django.utils import timezone

# Create your models here.

class StudentProfile(models.Model):
    """Student-specific information"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
        verbose_name="Utilisateur"
    )
    
    # === Education Info ===
    LEVEL_CHOICES = [
        ('paces', 'PACES'),
        ('2ème année', '2ème année'),
        ('3ème année', '3ème année'),
        ('4ème année', '4ème année'),
        ('5ème année', '5ème année'),
        ('6ème année', '6ème année'),
        ('interne', 'Interne'),
    ]
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Niveau d'études"
    )
    institution = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Établissement"
    )
    student_id_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Numéro IM"
    )
    
    # === Status ===
    is_active_student = models.BooleanField(
        default=True,
        verbose_name="Étudiant actif"
    )
    
    # === Contact & Social ===
    facebook = models.URLField(blank=True, null=True, verbose_name="Facebook")
    instagram = models.URLField(blank=True, null=True, verbose_name="Instagram")
    
    # === Preferences ===
    preferred_learning_style = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('visual', 'Visuel'),
            ('auditory', 'Auditif'),
            ('kinesthetic', 'Kinesthésique'),
            ('reading', 'Lecture/Écriture')
        ],
        verbose_name="Style d'apprentissage préféré"
    )
    
    # === Timestamps ===
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    
    # === Methods ===
    def __str__(self):
        return f"Étudiant: {self.user.display_name}"
    
    def active_enrollments(self):
        """Get active enrollments"""
        return self.student_enrollment.filter(is_active=True)
    
    def save(self, *args, **kwargs):
        """Ensure user is flagged as student and sync premium status"""
        if not self.user.is_student:
            self.user.is_student = True
            self.user.save(update_fields=['is_student'])
        
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Profil Étudiant"
        verbose_name_plural = "Profils Étudiants"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level']),
        ]


