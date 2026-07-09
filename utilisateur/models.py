
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


class User(AbstractUser):
    """
    Core authentication model - Only essential auth & contact info
    """
    GENDER_CHOICES = [
        ('M', 'Homme'),
        ('F', 'Femme'),
    ]
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
        verbose_name="Genre"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de naissance"
    )
    # === Contact Info ===
    phone_regex = RegexValidator(
        regex=r'^03[2-8]\d{7}$',
        message="Numéro malgache requis (ex: 0341234567)"
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=10,
        unique=True,
        blank=True,
        null=True,
        help_text="Ex: 0341234567 (sans +261 ni espaces)"
    )
    bio = models.TextField(
        blank=True, null=True,
        verbose_name="Biographie",
        help_text="Présentation professionnelle ou personnelle"
    )
    profile_pic = models.ImageField(
        upload_to='profile_pics/%Y/%m/',
        blank=True,
        null=True,
        default='profile_pics/default.png',
        verbose_name="Photo de profil"
    )
   
    # Email should be unique and required
    email = models.EmailField(unique=True, blank=False, null=False)
    
    # === Role Flags (for quick filtering) ===
    is_student = models.BooleanField(default=False, db_index=True)
    is_teacher = models.BooleanField(
        default=False, 
        db_index=True,
        verbose_name="Est un enseignant"
    )
    # === Django Auth Fixes ===
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )
                           
    @property
    def legacy_level_of_study(self):
        """Temporary: Get level from student profile"""
        if hasattr(self, 'student_profile'):
            return self.student_profile.level
        return None
 
    # === Profile Access ===
    @property
    def active_profile(self):
        """
        Get the current active profile based on role flags.
        Useful for views that need profile-specific data.
        """
        if self.is_student and hasattr(self, 'student_profile'):
            return self.student_profile
        return None
    
    @property
    def display_name(self):
        """Consistent name display across the app"""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name or self.username
     
    @property
    def age(self):
        """Calculate age from date_of_birth"""
        if not self.date_of_birth:
            return None
        
        today = timezone.now().date()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    
    # === Validation ===
    def clean(self):
        """Validate role consistency"""
        super().clean()
    
    def save(self, *args, **kwargs):
        """Ensure email is lowercase for consistency"""
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)
    
    def get_primary_role(self):
        """Get the user's primary role based on flags"""
        if self.is_student:
            return 'student'
        else:
            return 'user'

    # === String Representation ===
    def __str__(self):
        return self.display_name
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['is_student']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['is_teacher']), 
            models.Index(fields=['is_teacher', 'is_active']),
        ]
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

