from django.db import models
from lecon.models import Chapter
from utilisateur.models import User
import os


class Importer (models.Model):
    FILE_TYPES = [
        ('docx', 'Word Document'),
        ('pptx', 'PowerPoint'),
        ('pdf', 'PDF'),
    ]
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, default=1)
    file_type = models.CharField(max_length=50, choices=FILE_TYPES)
    file = models.FileField(upload_to='lessons/uploads/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    page_count = models.IntegerField(default=0, blank=True, null=True)
    processed = models.BooleanField(default=False)  # For extraction status

    def __str__(self):
        return self.title or f"{self.file.name} - {self.uploaded_at}"
    
    def save(self, *args, **kwargs):
        # Only set title if not already set and file exists
        if not self.title and hasattr(self, 'file') and self.file:
            # Extract filename without extension
            filename = os.path.basename(self.file.name)
            self.title = os.path.splitext(filename)[0]
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Document importé"
        verbose_name_plural = "Documents importés"
        ordering = ['-uploaded_at']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['-uploaded_at']),  # Already in ordering but explicit
            models.Index(fields=['processed', 'uploaded_at']),  # For processing queue
            models.Index(fields=['chapter', 'processed']),  # Chapter's processed status
            models.Index(fields=['file_type', 'chapter']),  # Filter by file type
            models.Index(fields=['processed']),  # Simple status filter
        ]   


NIVEAU_CHOICES = [
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
    ("5", "5"),
    ("6", "6"),
    ("7", "7"),
    ("8", "8"),
    ("9", "9"),
]


class Copy (models.Model):
    chapter = models.ForeignKey (Chapter, on_delete=models.CASCADE)
    heading_level = models.CharField (max_length=50, choices=NIVEAU_CHOICES, verbose_name="Niveau titre", blank=True, null=True)
    heading = models.CharField (max_length=500, verbose_name="Titre", blank=True, null=True)
    is_qe = models.BooleanField ("Etre question d'examen",default=False, null=True, blank=True)
    content = models.JSONField(verbose_name="Contenu", blank=True, null=True)   
    explanation = models.TextField (verbose_name="Explication", blank=True, null=True)
    image = models.ImageField(upload_to="lessons/", blank=True, null=True)
    caption = models.TextField(("Légende"), blank=True, null=True)
    table = models.JSONField(blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    importer = models.ForeignKey(Importer, on_delete=models.SET_NULL, null=True, blank=True, related_name='copies')
 
    def __str__(self) -> str:
        return f"{self.chapter} - {self.heading}" or "Pas de titre"
    
    class Meta:
        verbose_name_plural = "Prise de note en salle"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['chapter']),  # All copies for a chapter
            models.Index(fields=['heading_level', 'chapter']),  # For hierarchical navigation
            models.Index(fields=['is_qe', 'chapter']),  # For exam questions filtering
            models.Index(fields=['chapter', 'id']),  # For pagination
            models.Index(fields=['heading']),  # Single column for heading searches
            models.Index(fields=['created_at']), # Version control of the copies
            models.Index(fields=['importer', 'chapter']),
        ]                 


class ResumeIA (models.Model):
    chapitre = models.ForeignKey(Chapter, verbose_name=("Chapitre"), on_delete=models.CASCADE)
    resume = models.TextField(("Résumé"))
    date = models.DateTimeField(("Date"), auto_now_add=True)
    mis_a_jour = models.DateTimeField(("Mis à jour le"), auto_now=True)

    def __str__(self):
        return f"Résumé par IA de {self.chapitre}"
    
    class Meta:
        verbose_name = "Résumé par intelligence artificielle"
        verbose_name_plural = "Résumés par intelligence artificielle"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['chapitre', '-date']),  # Latest IA summary per chapter
            models.Index(fields=['-date']),  # All IA summaries by date
            models.Index(fields=['mis_a_jour']),  # For update tracking
            models.Index(fields=['chapitre', 'mis_a_jour']),  # Chapter's updated summaries
        ]


class Resume (models.Model):
    chapitre = models.ForeignKey(Chapter, verbose_name=("Chapitre"), on_delete=models.CASCADE)
    createur = models.ForeignKey(User, verbose_name=("Créé par"), on_delete=models.CASCADE)
    resume = models.TextField(("Résumé"))
    date = models.DateTimeField(("Date"), auto_now_add=True)
    mis_a_jour = models.DateTimeField(("Mis à jour le"), auto_now=True)

    def __str__(self):
        return f"Résumé par IA de {self.chapitre}"
    
    class Meta:
        verbose_name = "Résumé"
        verbose_name_plural = "Résumés"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['createur', '-date']),  # User's summaries by date
            models.Index(fields=['chapitre', '-date']),  # Chapter summaries by date
            models.Index(fields=['createur', 'chapitre']),  # User's summary per chapter
            models.Index(fields=['mis_a_jour']),  # For update tracking
            models.Index(fields=['-date']),  # All summaries by date
        ]


class UserAnnotation (models.Model):
    """Store user highlights and notes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    copy = models.ForeignKey(Copy, on_delete=models.CASCADE)
    highlighted_text = models.TextField(blank=True, null=True)
    user_note = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=20, default='yellow')  # Highlight color
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Annotation utilisateur"
        verbose_name_plural = "Annotations utilisateur"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['user', '-created_at']),  # User's recent annotations
            models.Index(fields=['copy', 'user']),  # All annotations on a copy
            models.Index(fields=['user', 'copy']),  # For checking duplicates (unique check)
            models.Index(fields=['updated_at']),  # For sync operations
            models.Index(fields=['copy', '-created_at']),  # Recent annotations on copy
            models.Index(fields=['user', 'copy', 'color']),  # User's color-coded annotations
        ]

    def __str__(self):
        return f"{self.user} - {self.copy.heading}"


class StudySession (models.Model):
    """Track student study time for each chapter"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(default=0)  # Total study time in seconds
    completed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Session d'étude"
        verbose_name_plural = "Sessions d'étude"
        indexes = [
            # Enhanced indexes
            models.Index(fields=['user', 'chapter', '-start_time']),  # User's recent sessions per chapter
            models.Index(fields=['chapter', '-start_time']),  # All recent sessions per chapter
            models.Index(fields=['user', '-start_time']),  # User's all recent sessions
            models.Index(fields=['completed', 'user']),  # User's completed sessions
            models.Index(fields=['user', 'completed', '-start_time']),  # User's completed sessions by date
            models.Index(fields=['duration_seconds']),  # For analyzing study duration
            models.Index(fields=['user', 'duration_seconds']),  # User's study duration patterns
        ]

    def __str__(self):
        return f"{self.user} - {self.chapter} - {self.duration_seconds}s"