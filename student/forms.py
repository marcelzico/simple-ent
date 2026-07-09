from django import forms 
from . models import StudentProfile


class StudentProfileForm(forms.ModelForm):
    """Formulaire COMPLET pour StudentProfile avec TOUS les champs du modèle"""
    
    class Meta:
        model = StudentProfile
        fields = '__all__'  # Prendre tous les champs
        exclude = ['user', 'created_at', 'updated_at']  # Exclure les champs auto
        
        widgets = {
            'profile_pic': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),

            'level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Université de Médecine'
            }),
            'student_id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IM2024001'
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/username'
            }),
            'instagram': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/username'
            }),
            'preferred_learning_style': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ne pas permettre la modification de l'utilisateur
        if 'user' in self.fields:
            self.fields['user'].disabled = True
            self.fields['user'].widget = forms.HiddenInput()
