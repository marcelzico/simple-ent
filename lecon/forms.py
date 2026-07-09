from django import forms
from .models import Unite, Chapter, UniteSection
from utilisateur.models import User
    

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Unite
        fields = ['title', 'level', 'semester']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={"class": "form-select"}),
            'semester': forms.Select(attrs={"class": 'form-select'}),
        }
 

class ChapterForm(forms.ModelForm):
    class Meta:
        model = Chapter
        fields = ['title', 'prof', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={"class": "form-control",}),
            'order': forms.NumberInput(attrs={'min': 1, "class": "form-control"}),
            'prof': forms.TextInput(attrs={"class": "form-control"}),
            'is_active': forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # if self.instance and self.instance.pk:
        #     self.fields['prof'].initial = self.instance.prof


class UniteSectionForm(forms.ModelForm):
    class Meta:
        model = UniteSection
        fields = ['title', 'chapters']  # Remove 'ue' as we set it in the view
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex : Anatomie viscérale, Sémilologie chirurgicale, ...'
            }),
            'chapters': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'title': 'Nom de la section',
            'chapters': 'Sélectionner les chapitres',
        }
        help_texts = {
            'chapters': 'Sélectionnez les chapitres qui font partie de cette section',
        }
    
    def __init__(self, *args, **kwargs):
        self.unite = kwargs.pop('unite', None)
        super().__init__(*args, **kwargs)
        
        # If unite is provided, filter chapters by that unite
        if self.unite:
            self.fields['chapters'].queryset = Chapter.objects.filter(
                ue=self.unite
            ).order_by('order')
        
        # Add CSS classes to form fields
        for field_name, field in self.fields.items():
            if field_name != 'chapters':  # Skip chapters as it has custom widget
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class ChapterSearchForm(forms.Form):
    q = forms.CharField(
        required=False, 
        label='Recherche',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': '🔍 Mots-clés dans les notes...'
        })
    )
    level = forms.ChoiceField(
        required=False, 
        choices=Unite.LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    semester = forms.ChoiceField(
        required=False, 
        choices=Unite.SEMESTRE,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    prof = forms.CharField(
        required=False, 
        label='Professeur',
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Nom du prof...'
        })
    )


class HeadingFilterForm(forms.Form):
    level = forms.ChoiceField(
        choices = Unite.LEVEL_CHOICES,
        label="Level",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-level': 'true'  # Custom marker for JS
        })
    )
    unite = forms.ModelChoiceField(
        queryset=Unite.objects.none(),
        label="Subject (Unité)",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-unite': 'true',
            'disabled': True
        })
    )
    heading_query = forms.CharField(
        label="Search Heading",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., diagnostic'})
    )


class ContentFilterForm(forms.Form):
    level = forms.ChoiceField(
        choices=Unite.LEVEL_CHOICES,
        label="Level",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-level': 'true'
        })
    )
    unite = forms.ModelChoiceField(
        queryset=Unite.objects.none(),
        label="Subject (Unité)",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-ajax-unite': 'true',
            'disabled': True
        })
    )
    content_query = forms.CharField(
        label="Search in Content",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., hypertension, treatment, diagnosis...'})
    )
    