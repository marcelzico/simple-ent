# users/forms.py - Enhanced
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import User
import re
from django.utils import timezone 
import os
from django.core.files.uploadedfile import UploadedFile
from django.db.models.fields.files import ImageFieldFile
from PIL import Image
import io
from django.core.files.base import ContentFile
from student.models import StudentProfile


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nom d\'utilisateur ou email',
            'autocomplete': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mot de passe',
            'autocomplete': 'current-password'
        })
    )
    remember_me = forms.BooleanField(
        required=False,
        label="Se souvenir de moi",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )


class UserProfileForm(forms.ModelForm):
    """Formulaire complet pour User avec TOUS les champs"""
    
    # Profile picture field - make it required=False for updates
    profile_pic = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
            'id': 'profile_pic_input'
        }),
        label="Photo de profil"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name','date_of_birth', 'bio', 'email', 'phone_number', 'gender', 'profile_pic']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre prénom'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Votre nom'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Parlez-nous de vous...',
                'rows': 4,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'exemple@domaine.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0341234567',
                'pattern': '03[2-8][0-9]{7}'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set help text for profile picture
        self.fields['profile_pic'].help_text = "Téléchargez une nouvelle photo (JPG, PNG, GIF - max 5MB)"


# ==================== ROLE-SPECIFIC FORMS ====================

class StudentProfileUpdateForm(forms.ModelForm):
    """Form for updating student profile independently"""
    
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Date de naissance"
    )
    
    class Meta:
        model = StudentProfile
        fields = ['date_of_birth', 'level', 'institution', 'student_id_number', 
                 'preferred_learning_style', 'facebook', 'instagram']
        widgets = {
            'level': forms.Select(attrs={
                'class': 'form-select',
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Université de Médecine',
            }),
            'student_id_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IM2024001',
            }),
            'preferred_learning_style': forms.Select(attrs={
                'class': 'form-select',
            }),
            'facebook': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/username',
            }),
            'instagram': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://instagram.com/username',
            }),
        }


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'exemple@domaine.com'
        }),
        help_text="Nous enverrons un email de confirmation à cette adresse"
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0341234567',
            'pattern': '03[2-4][0-9]{7}',
            'title': 'Format: 032, 033 ou 034 suivi de 7 chiffres'
        }),
        help_text="Format malgache: 032, 033 ou 034 suivi de 7 chiffres"
    )
    
    terms_accepted = forms.BooleanField(
        required=True,
        label="J'accepte les conditions d'utilisation",
        error_messages={'required': 'Vous devez accepter les conditions'}
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choisissez un nom d\'utilisateur'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to password fields
        self.fields['password1'].widget.attrs['class'] = 'form-control'
        self.fields['password2'].widget.attrs['class'] = 'form-control'
        
        # Custom error messages
        for field_name in self.fields:
            field = self.fields[field_name]
            if 'required' in field.error_messages:
                field.error_messages['required'] = 'Ce champ est obligatoire'
    
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                'Cette adresse email est déjà utilisée. '
                'Essayez de vous connecter ou utilisez une autre adresse.'
            )
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError(
                'Ce nom d\'utilisateur est déjà pris. '
                'Veuillez en choisir un autre.'
            )
        if len(username) < 3:
            raise ValidationError('Le nom d\'utilisateur doit contenir au moins 3 caractères')
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError(
                'Le nom d\'utilisateur ne peut contenir que des lettres, '
                'chiffres et les caractères @/./+/-/_'
            )
        return username
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone:
            # Clean the number
            phone = ''.join(filter(str.isdigit, phone))
            
            if len(phone) == 9 and phone.startswith(('32', '33', '34')):
                phone = '0' + phone
            
            if len(phone) != 10:
                raise ValidationError("Le numéro doit contenir 10 chiffres.")
            
            if not phone.startswith(('032', '033', '034')):
                raise ValidationError("Le numéro doit commencer par 032, 033 ou 034.")
            
            # Check if phone number already exists
            if User.objects.filter(phone_number=phone).exists():
                raise ValidationError("Ce numéro de téléphone est déjà utilisé.")
        
        return phone
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        
        if commit:
            user.save()
        
        return user

