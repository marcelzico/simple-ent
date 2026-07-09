from django import forms
from .models import Copy, NIVEAU_CHOICES, Importer, Resume, ResumeIA
import os


class CopyForm(forms.ModelForm):
    class Meta:
        model = Copy
        fields = ['heading_level', 'heading','is_qe', 'content', 'explanation', 
                 'image', 'caption', 'table']
        widgets = {
            'heading': forms.TextInput(attrs={'class': 'form-control'}),
            'is_qe': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'content': forms.Textarea(attrs={'rows': 5, 'class': 'richeditor form-control'}),
            'explanation': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'heading_level': forms.Select(choices=NIVEAU_CHOICES, attrs={'class': 'form-control-select'}),
            'caption': forms.Textarea(attrs={'class': 'form-control'}),
            'table': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
        }
 
    def __init__(self, *args, **kwargs):
        self.chapter = kwargs.pop('chapter', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)



class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Importer
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.docx,.pptx',  # Limit file types
            }),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            ext = os.path.splitext(file.name)[1].lower()
            allowed_extensions = ['.pdf', '.docx', '.pptx']
            if ext not in allowed_extensions:
                raise forms.ValidationError(
                    'Type de fichier non supporté. Utilisez PDF, Word (.docx) ou PowerPoint (.pptx).'
                )
            
            # Limit file size (e.g., 50MB)
            max_size = 50 * 1024 * 1024  # 50MB
            if file.size > max_size:
                raise forms.ValidationError(
                    f'Le fichier est trop volumineux. Taille maximale : {max_size/1024/1024}MB'
                )
        
        return file


class ResumeIaForm (forms.ModelForm):
    class Meta:
        model = ResumeIA
        fields = ['resume']
        widgets={
            'resume':forms.Textarea(attrs={'class': 'form-control'})
        }


class ResumeForm (forms.ModelForm):
    class Meta:
        model = Resume
        fields = ['resume']
        widgets={
            'resume':forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'col': 40})
        }


from django.forms.widgets import Input


class MultipleFileInput(forms.widgets.Input):
    input_type = 'file'
    template_name = 'django/forms/widgets/file.html'
    needs_multipart_form = True

    def __init__(self, attrs=None):
        # No extra validation – just pass attrs to parent
        super().__init__(attrs)



class BulkUploadForm(forms.Form):
    csv_file = forms.FileField(label='Select CSV file')



class FolderImportForm(forms.Form):
    folder_path = forms.CharField(
        label="Chemin du dossier",
        max_length=500,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '/chemin/absolu/vers/le/dossier'
        })
    )



class ChapterDataFolderImportForm(forms.Form):
    folder_path = forms.CharField(
        label="Chemin du dossier racine",
        max_length=500,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '/chemin/absolu/vers/le/dossier'})
    )
    auto_create_missing = forms.BooleanField(
        label="Créer automatiquement les niveaux/UE/chapitres manquants",
        required=False,
        initial=True
    )
