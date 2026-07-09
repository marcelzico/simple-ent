from django import forms
from django.forms import DateTimeInput, inlineformset_factory
from .models import MCQQuiz, QAQuiz, MCQ, QuestionAnswer, QAAttempt, TrueFalseQuiz
from lecon.models import Chapter     
from django.core.exceptions import ValidationError


class MCQForm(forms.ModelForm):
    class Meta:
        model = MCQ
        fields = ['question', 'option1', 'option2', 'option3', 'option4', 'correct_option', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'option1': forms.TextInput(attrs={'class': 'form-control'}),
            'option2': forms.TextInput(attrs={'class': 'form-control'}),
            'option3': forms.TextInput(attrs={'class': 'form-control'}),
            'option4': forms.TextInput(attrs={'class': 'form-control'}),
            'explanation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }


class QAForm(forms.ModelForm):
    class Meta:
        model = QuestionAnswer
        fields = ['question', 'sample_answer', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'sample_answer': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'explanation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }
    

class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'


class BaseQuizForm:
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.subject = kwargs.pop('subject', None)
        super().__init__(*args, **kwargs)
        
        if self.user and self.user.is_authenticated:
            self.filter_querysets()

    def filter_querysets(self):
        # Filter chapters based on subject
        if self.subject:
            chapters_queryset = Chapter.objects.filter(ue=self.subject)
        else:
            chapters_queryset = Chapter.objects.none()
        
        self.fields['chapters'].queryset = chapters_queryset
        
        # Set initial queryset for questions
        if hasattr(self, 'get_question_model'):
            question_model = self.get_question_model()
            if self.subject:
                self.fields['questions'].queryset = question_model.objects.filter(chapter__ue=self.subject)
            else:
                self.fields['questions'].queryset = question_model.objects.none()


class MCQQuizForm(BaseQuizForm, forms.ModelForm):
    def get_question_model(self):
        return MCQ
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('max_attempts'):
            self.fields['max_attempts'].initial = 1
        if not self.initial.get('score_to_pass'):
            self.fields['score_to_pass'].initial = 50
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise ValidationError("End date must be after start date")
        
        return cleaned_data
    
    def clean_questions(self):
        """Override validation for questions field since they're loaded via AJAX"""
        question_ids = self.data.getlist('questions') if hasattr(self, 'data') else []
        
        if not question_ids:
            raise ValidationError("Please select at least one question.")
        
        try:
            question_ids = [int(qid) for qid in question_ids if qid]
        except ValueError:
            raise ValidationError("Invalid question IDs provided.")
        
        valid_questions = MCQ.objects.filter(id__in=question_ids)
        
        if len(valid_questions) != len(question_ids):
            found_ids = set(valid_questions.values_list('id', flat=True))
            missing_ids = set(question_ids) - found_ids
            raise ValidationError(f"Invalid question IDs: {missing_ids}")
        
        return valid_questions

    class Meta:
        model = MCQQuiz
        fields = ['title', 'description', 'chapters', 'questions', 
                 'time_limit', 'max_attempts', 'score_to_pass', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'chapters': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'questions': forms.SelectMultiple(attrs={
                'class': 'form-select', 
                'id': 'id_questions',
                'style': 'display: none;'
            }),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1', 
                'value': '1'
            }),
            'score_to_pass': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '0', 
                'max': '100',
                'value': '50'
            }),
        }


class QAQuizForm(BaseQuizForm, forms.ModelForm):
    def get_question_model(self):
        from quizzes.models import QuestionAnswer
        return QuestionAnswer
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('max_attempts'):
            self.fields['max_attempts'].initial = 1
        if not self.initial.get('score_to_pass'):
            self.fields['score_to_pass'].initial = 50
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError("End date must be after start date")
        
        return cleaned_data
    
    def clean_questions(self):
        """Override validation for questions field since they're loaded via AJAX"""
        question_ids = self.data.getlist('questions') if hasattr(self, 'data') else []
        
        if not question_ids:
            raise ValidationError("Please select at least one question.")
        
        try:
            question_ids = [int(qid) for qid in question_ids if qid]
        except ValueError:
            raise ValidationError("Invalid question IDs provided.")
        
        from .models import QuestionAnswer
        valid_questions = QuestionAnswer.objects.filter(id__in=question_ids)
        
        if len(valid_questions) != len(question_ids):
            found_ids = set(valid_questions.values_list('id', flat=True))
            missing_ids = set(question_ids) - found_ids
            raise ValidationError(f"Invalid question IDs: {missing_ids}")
        
        return valid_questions

    class Meta:
        model = QAQuiz
        fields = ['title', 'description', 'chapters', 'questions',
                 'time_limit', 'max_attempts', 'score_to_pass', 'start_date', 'end_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'chapters': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'questions': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'id': 'id_questions',
                'style': 'display: none;'
            }),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'max_attempts': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '1', 
                'value': '1'
            }),
            'score_to_pass': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': '0', 
                'max': '100',
                'value': '50'
            }),
        }


class QAAttemptForm (forms.ModelForm):
    class Meta:
        model = QAAttempt
        fields = ['answers']


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(label='Select a CSV file')


class TrueFalseForm(forms.ModelForm):
    class Meta:
        model = TrueFalseQuiz
        fields = ['question', 'answer', 'explanation', 'time_limit']
        widgets = {
            'question': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'answer': forms.Select(
                attrs={'class': 'form-control'}, 
                choices=[(True, 'True'), (False, 'False')]
            ),
            'explanation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'time_limit': forms.NumberInput(attrs={'class': 'form-control', 'min': '10'}),
        }
        help_texts = {
            'question': 'Enter the true/false statement',
            'answer': 'Select whether the statement is true or false',
            'explanation': 'Optional: Explain why the answer is true or false',
            'time_limit': 'Time limit in seconds for answering this question',
        }
    
    def clean_time_limit(self):
        time_limit = self.cleaned_data.get('time_limit')
        if time_limit < 10:
            raise forms.ValidationError("Time limit must be at least 10 seconds")
        return time_limit

