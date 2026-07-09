from django.db import models
from utilisateur.models import User

class Unite(models.Model):
    SEMESTRE = (
        ('S1', 'S1'),
        ('S2', 'S2'),
    )
    LEVEL_CHOICES = [
        ('', 'Choisir niveau'), 
        ('paces', 'PACES'),
        ('2ème année', '2ème année'),
        ('3ème année', '3ème année'),
        ('4ème année', '4ème année'),
        ('5ème année', '5ème année'),
        ('6ème année', '6ème année'),
        ('Prépa IQ', 'Prépa IQ'),
        ('Autre', 'Autre'),
    ]

    title = models.CharField(max_length=200)
    level = models.CharField(("Niveau"), max_length=50, choices=LEVEL_CHOICES,  default="4ème année")
    semester = models.CharField(("Semestre"), max_length=50, choices=SEMESTRE)
    # created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subjects_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    teachers = models.ManyToManyField(
        'utilisateur.User',
        related_name='teaching_unites',
        blank=True,
        verbose_name="Enseignants (titulaire et assistants)",
        help_text="Sélectionnez les enseignants qui peuvent gérer cette unité"
    )
    
    # === NOUVEAU: Enseignant principal (optionnel) ===
    main_teacher = models.ForeignKey(
        'utilisateur.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='main_teaching_unites',
        verbose_name="Enseignant principal",
        help_text="Enseignant titulaire ou responsable principal"
    )
    
    def __str__(self):
        return f"{self.title} - {self.level}"
    
    def get_teachers_list(self):
        """Retourne la liste des enseignants"""
        return self.teachers.all()
    
    def is_teacher(self, user):
        """Vérifie si un utilisateur est enseignant de cette unité"""
        if not user.is_authenticated:
            return False
        return self.teachers.filter(id=user.id).exists()
    
    class Meta:
        verbose_name = "Unité d'enseignement"
        verbose_name_plural = "Unités d'enseignement"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['level', 'semester']),  # For filtering by level/semester
            models.Index(fields=['title']),  # For title searches
            models.Index(fields=['-created_at']),  # For reverse chronological order
            models.Index(fields=['updated_at']),  # For tracking modifications
            models.Index(fields=['semester', 'level']),  # Alternative ordering
            models.Index(fields=['main_teacher']),
        ]        
    
    # @classmethod
    # def can_create(cls, user):
    #     return user.is_teacher or user.is_superuser or user.is_editor or user.is_admin
   

class Chapter(models.Model):
    ue = models.ForeignKey(Unite, on_delete=models.CASCADE, related_name='chapters')
    title = models.CharField(max_length=200)
    prof = models.CharField(("Nom du prof. "), max_length=200, blank=True, null=True)
    order = models.PositiveIntegerField(null=True, blank=True)
    is_active = models.BooleanField(("Actif"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def can_be_edited_by(self, user):
        """Vérifie si un utilisateur peut modifier ce chapitre"""
        if user.is_superuser:
            return True
        if not user.is_teacher:
            return False
        # L'enseignant peut modifier si son unité lui appartient
        return self.ue.is_teacher(user)


    class Meta:
        ordering = ['order']
        unique_together = ['ue', 'order']
        verbose_name = "Chapitre"
        verbose_name_plural = "Chapitres"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['ue', 'order']),  # Already covered by unique_together but explicit
            models.Index(fields=['is_active', 'ue']),  # For active chapters per UE
            models.Index(fields=['ue', 'is_active', 'order']),  # Optimized composite
            models.Index(fields=['prof']),  # If you search by professor name
            models.Index(fields=['updated_at']),  # For sync operations
            models.Index(fields=['-created_at']),  # For latest chapters
            models.Index(fields=['ue', '-created_at']),  # Latest chapters per UE
        ]    
  
    def __str__(self):
        return f"{self.title}"
    

class UniteSection(models.Model):
    title = models.CharField(max_length=100) 
    ue = models.ForeignKey(Unite, on_delete=models.CASCADE)
    chapters = models.ManyToManyField(Chapter)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Section d'unité d'enseignement"
        verbose_name_plural = "Sections d'unité d'enseignement"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['ue', 'title']),  # Reversed for UE-first queries
            models.Index(fields=['ue']),  # For all sections of a UE
            models.Index(fields=['-created_at']),  # For latest sections
            models.Index(fields=['updated_at']),  # For tracking updates
            models.Index(fields=['ue', '-created_at']),  # Latest sections per UE
        ]        
    
    def __str__(self):
        return str(f"{self.ue.title} - {self.title}")
    
    