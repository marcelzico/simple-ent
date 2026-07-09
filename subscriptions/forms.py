# subscription/forms.py
from django import forms
from django.core.exceptions import ValidationError
from .models import Payment, Subscription, Feature
from student.models import StudentProfile
from django.utils import timezone
from datetime import date


class PaymentForm(forms.ModelForm):
    """Form for students to make payments"""
    
    class Meta:
        model = Payment
        fields = [
            'feature', 'paid_with', 'amount', 
            'phone_number_of_payment', 'reference_of_payment',
            'description'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add any additional information about your payment...'
            }),
            'phone_number_of_payment': forms.TextInput(attrs={
                'placeholder': '0341234567'
            }),
            'reference_of_payment': forms.TextInput(attrs={
                'placeholder': 'Transaction reference'
            }),
        }
        labels = {
            'phone_number_of_payment': 'Phone Number',
            'reference_of_payment': 'Transaction Reference',
        }
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        
        # Only show active features
        self.fields['feature'].queryset = Feature.objects.all().order_by('price')
        
        # Set initial amount based on feature
        if 'feature' in self.data:
            try:
                feature_id = int(self.data.get('feature'))
                feature = Feature.objects.get(id=feature_id)
                self.fields['amount'].initial = feature.price
            except (ValueError, Feature.DoesNotExist):
                pass
    
    def clean(self):
        cleaned_data = super().clean()
        feature = cleaned_data.get('feature')
        amount = cleaned_data.get('amount')
        paid_with = cleaned_data.get('paid_with')
        phone_number = cleaned_data.get('phone_number_of_payment')
        
        # Validate amount matches feature price
        if feature and amount:
            if amount != feature.price:
                raise ValidationError(
                    f"Amount must be exactly {feature.price} Ariary for {feature.name}"
                )
        
        # Validate phone number for mobile payments
        if paid_with != 'cash' and not phone_number:
            raise ValidationError("Phone number is required for mobile money payments")
        
        return cleaned_data
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        if self.student:
            payment.student = self.student
        
        if commit:
            payment.save()
        return payment


class StudentSubscriptionForm(forms.ModelForm):
    """Form for students to create subscription requests"""
    
    class Meta:
        model = Subscription
        fields = [
            'payment', 'feature', 'planning_date_to_start', 'description'
        ]
        widgets = {
            'planning_date_to_start': forms.DateInput(attrs={
                'type': 'date',
                'min': date.today().isoformat()
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add any additional information about your subscription request...'
            }),
        }
        labels = {
            'planning_date_to_start': 'Planned Start Date (optional)',
        }
    
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.student:
            # Only show approved payments for this student
            self.fields['payment'].queryset = Payment.objects.filter(
                student=self.student,
                payement_status='approved'
            ).order_by('-created_at')
            
            # Only show features
            self.fields['feature'].queryset = Feature.objects.all().order_by('price')
        else:
            # If no student, show no payments
            self.fields['payment'].queryset = Payment.objects.none()
        
        # Students can't see notes field
        if self.user and not self.user.is_staff:
            if 'notes' in self.fields:
                del self.fields['notes']
    
    def clean(self):
        cleaned_data = super().clean()
        payment = cleaned_data.get('payment')
        planning_date = cleaned_data.get('planning_date_to_start')
        
        # Check if student was passed to form
        if not self.student:
            raise ValidationError("Student information is missing")
        
        # Validate payment belongs to student
        if payment and payment.student != self.student:
            raise ValidationError("Selected payment does not belong to you")
        
        # Validate payment is approved
        if payment and payment.payement_status != 'approved':
            raise ValidationError("Selected payment is not approved yet")
        
        # Check if payment is already used
        if payment:
            existing_sub = Subscription.objects.filter(
                payment=payment,
                payement_status__in=['pending', 'approved', 'active']
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_sub.exists():
                raise ValidationError("This payment is already used in another subscription")
        
        # Validate planning date
        if planning_date and planning_date < date.today():
            raise ValidationError("Planning date cannot be in the past")
        
        return cleaned_data
    
    def save(self, commit=True):
        subscription = super().save(commit=False)
        
        # Set the student
        subscription.student = self.student
        
        # Set amount
        if subscription.payment:
            subscription.amount = subscription.payment.amount
        elif subscription.feature:
            subscription.amount = subscription.feature.price
        
        if commit:
            subscription.save()
        return subscription
    def save(self, commit=True):
        subscription = super().save(commit=False)
        
        # Set student from form
        if self.student:
            subscription.student = self.student
        
        # Set amount from payment or feature
        if subscription.payment:
            subscription.amount = subscription.payment.amount
        elif subscription.feature:
            subscription.amount = subscription.feature.price
        
        if commit:
            subscription.save()
        return subscription


class AdminPaymentForm(forms.ModelForm):
    """Form for admin to review payments"""
    
    class Meta:
        model = Payment
        fields = ['payement_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add notes for the student (visible when rejected)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only show status options that make sense for admin
        self.fields['payement_status'].choices = [
            ('approved', 'Vérifié'),
            ('rejected', 'Refusé'),
        ]
        
        # Make notes required when rejecting
        if 'payement_status' in self.data and self.data.get('payement_status') == 'rejected':
            self.fields['notes'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('payement_status')
        notes = cleaned_data.get('notes')
        
        if status == 'rejected' and not notes:
            raise ValidationError("Notes are required when rejecting a payment")
        
        return cleaned_data
    
    def save(self, commit=True):
        payment = super().save(commit=False)
        
        if self.user and payment.payement_status != 'pending':
            payment.approved_by = self.user
            payment.approved_at = timezone.now()
        
        if commit:
            payment.save()
        return payment


class AdminSubscriptionForm(forms.ModelForm):
    """Form for admin to review subscriptions"""
    
    class Meta:
        model = Subscription
        fields = ['payement_status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add notes for the student'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit status choices for admin
        self.fields['payement_status'].choices = [
            ('approved', 'Approuvé'),
            ('rejected', 'Refusé'),
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('payement_status')
        notes = cleaned_data.get('notes')
        
        if status == 'rejected' and not notes:
            raise ValidationError("Notes are required when rejecting a subscription")
        
        return cleaned_data
    
    def save(self, commit=True):
        subscription = super().save(commit=False)
        
        if self.user and subscription.payement_status != 'pending':
            subscription.approved_by = self.user
            subscription.approved_at = timezone.now()
        
        if commit:
            subscription.save()
        return subscription


class FeatureForm(forms.ModelForm):
    """Form for managing features (admin only)"""
    
    class Meta:
        model = Feature
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter feature name'}),
            'code': forms.TextInput(attrs={'placeholder': 'Unique feature code'}),
            'validity_day_number': forms.NumberInput(attrs={'min': 1}),
            'price': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'mcq_features': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'mcq_exam_feature': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'qa_features': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'qa_exam_feature': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
            'tf_features': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
        }

