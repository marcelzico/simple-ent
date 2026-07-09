from django import forms
from django.forms import inlineformset_factory
from lecon.models import Unite, Chapter
from quizzes.models import MCQ, QuestionAnswer, TrueFalseQuiz, MCQQuiz, QAQuiz
from quizlet_copy.models import FlashcardSet, Flashcard
from clinical_case_simple.models import Enoncé, QCM, QestionRéponse, VraiFaux, Illustraion
from django.contrib.auth import get_user_model
from utilisateur.models import User
from .models import TeacherProfile

User = get_user_model()


# ==================== FORMULAIRES UNITÉS ====================

class UniteForm(forms.ModelForm):
    """Formulaire pour créer/modifier une unité d'enseignement"""
    
    class Meta:
        model = Unite
        fields = ['title', 'level', 'semester']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Anatomie, Physiologie, ...'
            }),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'semester': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'title': 'Titre de l\'unité',
            'level': 'Niveau',
            'semester': 'Semestre',
        }


class UniteTeachersForm(forms.ModelForm):
    """Formulaire pour ajouter des enseignants à une unité"""
    
    teachers = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_teacher=True),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
        required=False,
        label="Enseignants (titulaire et assistants)"
    )
    
    main_teacher = forms.ModelChoiceField(
        queryset=User.objects.filter(is_teacher=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Enseignant principal"
    )
    
    class Meta:
        model = Unite
        fields = ['teachers', 'main_teacher']


# ==================== FORMULAIRES CHAPITRES ====================

class ChapterForm(forms.ModelForm):
    """Formulaire pour créer/modifier un chapitre"""
    
    class Meta:
        model = Chapter
        fields = ['title', 'prof', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du chapitre'}),
            'prof': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du professeur'}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Titre',
            'prof': 'Professeur',
            'order': 'Ordre d\'affichage',
            'is_active': 'Chapitre actif',
        }


# ==================== FORMULAIRES QCM ====================

class MCQForm(forms.ModelForm):
    """Formulaire pour créer/modifier un QCM"""
    
    class Meta:
        model = MCQ
        fields = ['question', 'option1', 'option2', 'option3', 'option4', 'correct_option', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'option1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 1'}),
            'option2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 2'}),
            'option3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 3 (optionnel)'}),
            'option4': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 4 (optionnel)'}),
            'correct_option': forms.Select(attrs={'class': 'form-select'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'placeholder': 'Secondes'}),
        }
        labels = {
            'question': 'Question',
            'option1': 'Option 1',
            'option2': 'Option 2',
            'option3': 'Option 3',
            'option4': 'Option 4',
            'correct_option': 'Option correcte',
            'explanation': 'Explication',
            'time_limit': 'Temps limite (secondes)',
        }


# ==================== FORMULAIRES QUESTIONS/RÉPONSES ====================

class QuestionAnswerForm(forms.ModelForm):
    """Formulaire pour créer/modifier une question/réponse"""
    
    class Meta:
        model = QuestionAnswer
        fields = ['question', 'sample_answer', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'sample_answer': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Exemple de réponse attendue...'}),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 60, 'placeholder': 'Secondes'}),
        }
        labels = {
            'question': 'Question',
            'sample_answer': 'Exemple de réponse',
            'explanation': 'Explication',
            'time_limit': 'Temps limite (secondes)',
        }


# ==================== FORMULAIRES VRAI/FAUX ====================

class TrueFalseForm(forms.ModelForm):
    """Formulaire pour créer/modifier une question Vrai/Faux"""
    
    class Meta:
        model = TrueFalseQuiz
        fields = ['question', 'answer', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'answer': forms.Select(attrs={'class': 'form-select'}, choices=[(True, 'Vrai'), (False, 'Faux')]),
            'explanation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'placeholder': 'Secondes'}),
        }
        labels = {
            'question': 'Question',
            'answer': 'Réponse correcte',
            'explanation': 'Explication',
            'time_limit': 'Temps limite (secondes)',
        }


# ==================== FORMULAIRES QUIZ COMPOSITES ====================

class MCQQuizForm(forms.ModelForm):
    """Formulaire pour créer/modifier un quiz QCM"""
    
    chapters = forms.ModelMultipleChoiceField(
        queryset=Chapter.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        required=True,
        label="Chapitres inclus"
    )
    
    questions = forms.ModelMultipleChoiceField(
        queryset=MCQ.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
        required=True,
        label="Questions QCM"
    )
    
    class Meta:
        model = MCQQuiz
        fields = ['title', 'description', 'time_limit', 'max_attempts', 'score_to_pass', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du quiz'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description...'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Minutes'}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Nombre maximum de tentatives'}),
            'score_to_pass': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'placeholder': 'Score minimal (%)'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Titre du quiz',
            'description': 'Description',
            'time_limit': 'Temps limite (minutes)',
            'max_attempts': 'Tentatives maximum',
            'score_to_pass': 'Score minimal pour réussir (%)',
            'start_date': 'Date de début',
            'end_date': 'Date de fin',
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        unite_id = kwargs.pop('unite_id', None)
        super().__init__(*args, **kwargs)
        
        if unite_id:
            chapters = Chapter.objects.filter(ue_id=unite_id, is_active=True)
            self.fields['chapters'].queryset = chapters
            
            # Filtrer les questions par chapitres de l'unité
            self.fields['questions'].queryset = MCQ.objects.filter(
                chapter__ue_id=unite_id,
                created_by=teacher
            ) if teacher else MCQ.objects.none()


class QAQuizForm(forms.ModelForm):
    """Formulaire pour créer/modifier un quiz QA"""
    
    chapters = forms.ModelMultipleChoiceField(
        queryset=Chapter.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        required=True,
        label="Chapitres inclus"
    )
    
    questions = forms.ModelMultipleChoiceField(
        queryset=QuestionAnswer.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '8'}),
        required=True,
        label="Questions QA"
    )
    
    class Meta:
        model = QAQuiz
        fields = ['title', 'description', 'time_limit', 'max_attempts', 'score_to_pass', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Titre du quiz'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description...'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Minutes'}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Nombre maximum de tentatives'}),
            'score_to_pass': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100, 'placeholder': 'Score minimal (%)'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Titre du quiz',
            'description': 'Description',
            'time_limit': 'Temps limite (minutes)',
            'max_attempts': 'Tentatives maximum',
            'score_to_pass': 'Score minimal pour réussir (%)',
            'start_date': 'Date de début',
            'end_date': 'Date de fin',
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        unite_id = kwargs.pop('unite_id', None)
        super().__init__(*args, **kwargs)
        
        if unite_id:
            chapters = Chapter.objects.filter(ue_id=unite_id, is_active=True)
            self.fields['chapters'].queryset = chapters
            self.fields['questions'].queryset = QuestionAnswer.objects.filter(
                chapter__ue_id=unite_id,
                created_by=teacher
            ) if teacher else QuestionAnswer.objects.none()


# ==================== FORMULAIRES FLASHCARDS ====================

class FlashcardSetForm(forms.ModelForm):
    """Formulaire pour créer/modifier un set de flashcards"""
    
    class Meta:
        model = FlashcardSet
        fields = ['title', 'description', 'is_public']
        widgets = {
            'title': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description...'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Chapitre',
            'description': 'Description',
            'is_public': 'Set public',
        }
    
    def __init__(self, *args, **kwargs):
        teacher = kwargs.pop('teacher', None)
        unite_id = kwargs.pop('unite_id', None)
        super().__init__(*args, **kwargs)
        
        if teacher and unite_id:
            chapters = Chapter.objects.filter(ue_id=unite_id, ue__teachers=teacher)
            self.fields['title'].queryset = chapters


class FlashcardForm(forms.ModelForm):
    """Formulaire pour créer/modifier une flashcard"""
    
    class Meta:
        model = Flashcard
        fields = ['term', 'definition']
        widgets = {
            'term': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Terme / Question...'}),
            'definition': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Définition / Réponse...'}),
        }
        labels = {
            'term': 'Terme / Question',
            'definition': 'Définition / Réponse',
        }


# ==================== FORMULAIRES CAS CLINIQUES ====================

class EnonceForm(forms.ModelForm):
    """Formulaire pour créer/modifier un énoncé de cas clinique"""
    
    class Meta:
        model = Enoncé
        fields = ['anonce_du_sujet', 'specialté', 'niveau_cible', 'publié']
        widgets = {
            'anonce_du_sujet': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Présentation du cas clinique...'}),
            'specialté': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Cardiologie, Neurologie...'}),
            'niveau_cible': forms.Select(attrs={'class': 'form-select'}),
            'publié': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'anonce_du_sujet': 'Présentation du cas',
            'specialté': 'Spécialité',
            'niveau_cible': 'Niveau cible',
            'publié': 'Publier ce cas',
        }


class ClinicalCaseQCMForm(forms.ModelForm):
    """Formulaire pour ajouter un QCM à un cas clinique"""
    
    class Meta:
        model = QCM
        fields = ['question', 'option1', 'option2', 'option3', 'option4', 'option5', 'réponse1', 'réponse2', 'réponse3', 'explication']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'option1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 1'}),
            'option2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 2'}),
            'option3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 3'}),
            'option4': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 4'}),
            'option5': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Option 5 (optionnel)'}),
            'réponse1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: A, B, AB, ABC', 'maxlength': '2'}),
            'réponse2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Réponse 2 (si multiple)', 'maxlength': '2'}),
            'réponse3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Réponse 3 (si multiple)', 'maxlength': '2'}),
            'explication': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
        }
        labels = {
            'réponse1': 'Réponse correcte (lettre)',
            'réponse2': 'Réponse correcte 2 (optionnel)',
            'réponse3': 'Réponse correcte 3 (optionnel)',
        }


class ClinicalCaseQRForm(forms.ModelForm):
    """Formulaire pour ajouter une question/réponse à un cas clinique"""
    
    class Meta:
        model = QestionRéponse
        fields = ['question', 'dificulté', 'réponse', 'explication']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'dificulté': forms.Select(attrs={'class': 'form-select'}),
            'réponse': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Réponse attendue...'}),
            'explication': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
        }


class ClinicalCaseVFForm(forms.ModelForm):
    """Formulaire pour ajouter une question Vrai/Faux à un cas clinique"""
    
    class Meta:
        model = VraiFaux
        fields = ['question', 'réponse', 'explication']
        widgets = {
            'question': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Question...'}),
            'réponse': forms.Select(attrs={'class': 'form-select'}, choices=[(True, 'Vrai'), (False, 'Faux')]),
            'explication': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Explication...'}),
        }


# ==================== FORMULAIRES PROFIL ====================

class TeacherProfileForm(forms.ModelForm):
    """Formulaire pour modifier le profil enseignant"""
    
    first_name = forms.CharField(max_length=150, required=False, label="Prénom")
    last_name = forms.CharField(max_length=150, required=False, label="Nom")
    email = forms.EmailField(required=True, label="Email")
    phone_number = forms.CharField(max_length=10, required=False, label="Téléphone")
    
    class Meta:
        model = TeacherProfile
        fields = ['titre', 'specialite', 'bio', 'bureau', 'heures_consultation', 'phone_pro', 'photo']
        widgets = {
            'titre': forms.Select(attrs={'class': 'form-select'}),
            'specialite': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Cardiologie'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Présentation professionnelle...'}),
            'bureau': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Bâtiment A, Bureau 12'}),
            'heures_consultation': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Lundi 14h-16h, Mercredi 10h-12h...'}),
            'phone_pro': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Téléphone professionnel'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['phone_number'].initial = user.phone_number
    
    def save(self, user, commit=True):
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        user.phone_number = self.cleaned_data['phone_number']
        if commit:
            user.save()
        
        profile = super().save(commit=False)
        profile.user = user
        if commit:
            profile.save()
        return profile


class NotificationPreferenceForm(forms.ModelForm):
    """Formulaire pour configurer les notifications"""
    
    class Meta:
        from teacher.models import NotificationPreference
        model = NotificationPreference
        fields = ['is_enabled', 'send_email', 'send_sms']
        widgets = {
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_email': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_sms': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'is_enabled': 'Activer cette notification',
            'send_email': 'Recevoir par email',
            'send_sms': 'Recevoir par SMS',
        }


