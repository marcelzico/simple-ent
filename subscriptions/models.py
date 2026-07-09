# models.py
from django.db import models
from django.db.models import Q, F
from django.utils import timezone
from django.core.validators import MinValueValidator, RegexValidator
import uuid
from datetime import timedelta, date
from student.models import StudentProfile
from django.core.exceptions import ValidationError
from utilisateur.models import User
from datetime import date, datetime
import json

# ========== FEATURE DEFINITIONS ==========
class Feature(models.Model):
    """Individual features with different access levels"""
    
    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['price']),
            models.Index(fields=['validity_day_number']),
        ]
        ordering = ['price', 'name']
        verbose_name = "Feature"
        verbose_name_plural = "Features"

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)

    # Usage counters
    mcq_features = models.PositiveIntegerField(
        default=0,
        help_text="Nombre maximum de QCM autorisé"
    )
    mcq_exam_feature = models.PositiveIntegerField(
        default=0,
        help_text="Nombre maximum de EXAMEN DE QCM autorisé"
    )
    qa_features = models.PositiveIntegerField(
        default=0,
        help_text="Nombre maximum de QUESTION ET REPONSE autorisé"
    )
    qa_exam_feature = models.PositiveIntegerField(
        default=0,
        help_text="Nombre maximum de EXAMEN DE QUESTION ET REPONSE autorisé"
    )
    tf_features = models.PositiveIntegerField(
        default=0,
        help_text="Nombre maximum de VRAIE OU FAUSSE question autorisé"
    )

    validity_day_number = models.PositiveIntegerField(
        help_text="Number of days the subscription is valid"
    )

    # Feature flags
    can_add_resume = models.BooleanField(default=False)
    can_add_notes = models.BooleanField(default=False)
    can_view_terminology = models.BooleanField(default=False)
    can_practice_terminology = models.BooleanField(default=False)
    can_view_public_flashcard = models.BooleanField(default=False)
    can_practice_quizlet_learning_mode = models.BooleanField(default=False)
    can_view_image_quiz = models.BooleanField(default=False)
    can_practice_image_quiz = models.BooleanField(default=False)
    can_ask_question = models.BooleanField(default=False)
    can_view_dicussion = models.BooleanField(default=False)
    can_add_own_terminology = models.BooleanField(default=False)
    can_add_own_flashcard = models.BooleanField(default=False)

    price = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_feature_list(self):
        """Return a list of enabled features"""
        features = []
        if self.can_add_resume:
            features.append("Add Resume")
        if self.can_add_notes:
            features.append("Add Notes")
        if self.can_view_terminology:
            features.append("View Terminology")
        if self.can_practice_terminology:
            features.append("Practice Terminology")
        if self.can_view_public_flashcard:
            features.append("View Quizlet")
        if self.can_practice_quizlet_learning_mode:
            features.append("Practice Quizlet Learning Mode")
        if self.can_view_image_quiz:
            features.append("View Image Quiz")
        if self.can_practice_image_quiz:
            features.append("Practice Image Quiz")
        if self.can_ask_question:
            features.append("Ask Questions")
        if self.can_view_dicussion:
            features.append("View Discussion")
        if self.can_add_own_terminology:
            features.append("Can add own terminology")
        if self.can_add_own_flashcard:
            features.append("Can add own flashcard")
        return features
    
    def get_quiz_limits_summary(self):
        """Get a summary of all quiz limits"""
        return {
            'mcq': self.mcq_features,
            'mcq_exam': self.mcq_exam_feature,
            'qa': self.qa_features,
            'qa_exam': self.qa_exam_feature,
            'tf': self.tf_features,
        }
    

# ========== MOBILE MONEY PROVIDERS ==========
class Payment(models.Model):
    """Supported mobile money providers with audit trail"""
    
    PROVIDER_CHOICES = [
        ('mvola', 'MVola'),
        ('orange', 'Orange Money'),
        ('airtel', 'Airtel Money'),
        ('cash', 'Payment direct'),
    ]
    PAYEMENT_STATUS = [
        ('pending', 'En attente'),
        ('approved', 'Vérifié'),
        ('rejected', 'Refusé'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.SET_NULL, null=True)
    feature = models.ForeignKey(Feature, on_delete=models.SET_NULL, null=True)
    paid_with = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    amount = models.PositiveIntegerField()
    
    phone_regex = RegexValidator(
        regex=r'^03[2-8]\d{7}$',
        message="Numéro malgache requis (ex: 0341234567)"
    )
    phone_number_of_payment = models.CharField(
        validators=[phone_regex],
        max_length=10,
        blank=True,
        null=True,
        help_text="Ex: 0341234567 (sans +261 ni espaces)"
    )
    reference_of_payment = models.CharField(max_length=15)

    description = models.TextField(blank=True, null=True)
    
    # Payment status and audit trail
    payement_status = models.CharField(
        max_length=50, 
        choices=PAYEMENT_STATUS, 
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    
    # Audit trail fields
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='approved_payments'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.feature} - {self.amount}"

    def clean(self):
        """Validate payment data"""
        if self.paid_with != 'cash' and not self.phone_number_of_payment:
            raise ValidationError(
                "Phone number is required for mobile money payments"
            )
        if self.amount < self.feature.price:
            raise ValidationError("Amount must be greater than {self.feature.price} Ar")
        
        # Ensure reference is unique for pending and approved payments
        if self.payement_status in ['pending', 'approved']:
            existing = Payment.objects.filter(
                reference_of_payment=self.reference_of_payment,
                payement_status__in=['pending', 'approved']
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError("Reference number already exists")

    def save(self, *args, **kwargs):
        """Override save to handle audit trail"""
        is_new = self.pk is None
        
        # Set approved_at timestamp when status changes to approved
        if not is_new:
            original = Payment.objects.get(pk=self.pk)
            if (original.payement_status != 'approved' and 
                self.payement_status == 'approved' and 
                not self.approved_at):
                self.approved_at = timezone.now()
        
        super().save(*args, **kwargs)

    def approve_payment(self, approved_by_user, notes=None):
        """Approve a pending payment with audit trail"""
        if self.payement_status != 'pending':
            raise ValidationError(f"Payment is already {self.payement_status}")
        
        if not approved_by_user:
            raise ValidationError("Approving user is required")
        
        self.payement_status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        
        if notes:
            self.notes = notes
        
        self.save()
        return self

    def reject_payment(self, approved_by_user, reason):
        """Reject a pending payment with audit trail"""
        if self.payement_status != 'pending':
            raise ValidationError(f"Payment is already {self.payement_status}")
        
        if not approved_by_user:
            raise ValidationError("Rejecting user is required")
        
        self.payement_status = 'rejected'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.notes = reason
        
        self.save()
        return self

    def get_payement_status_display(self):
        """Get human-readable payment status"""
        status_dict = dict(self.PAYEMENT_STATUS)
        return status_dict.get(self.payement_status, self.payement_status)

    def get_audit_info(self):
        """Get audit information for this payment"""
        audit_info = {
            'status': self.payement_status,
            'status_display': self.get_payement_status_display(),
            'notes': self.notes,
        }
        
        if self.approved_by:
            audit_info.update({
                'reviewed_by': self.approved_by.get_full_name() or self.approved_by.username,
                'reviewed_at': self.approved_at.strftime('%Y-%m-%d %H:%M:%S') if self.approved_at else 'N/A',
            })
        else:
            audit_info.update({
                'reviewed_by': 'Not yet reviewed',
                'reviewed_at': 'N/A',
            })
        
        return audit_info

    @classmethod
    def get_pending_payments(cls):
        """Get all pending payments"""
        return cls.objects.filter(payement_status='pending')

    @classmethod
    def get_student_payments(cls, student):
        """Get all payments for a specific student"""
        return cls.objects.filter(student=student).order_by('-created_at')

    @classmethod
    def get_reviewed_by_user(cls, user):
        """Get all payments reviewed by a specific user"""
        return cls.objects.filter(approved_by=user).exclude(payement_status='pending')


# ========== SUBSCRIPTION PLANS ==========
class Subscription(models.Model):
    
    SUBSCRIPTION_STATUS = [
        ('pending', 'En attente'),
        ('approved', 'Approuvé'),
        ('rejected', 'Refusé'),
        ('expired', 'Expiré'),
        ('active', 'Actif'),
    ]

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    feature = models.ForeignKey(Feature, on_delete=models.SET_NULL, null=True)
    
    # Subscription dates
    planning_date_to_start = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    
    # Usage tracking
    mcq_attempts_used = models.PositiveIntegerField(default=0)
    mcq_exam_attempts_used = models.PositiveIntegerField(default=0)
    qa_attempts_used = models.PositiveIntegerField(default=0)
    qa_exam_attempts_used = models.PositiveIntegerField(default=0)
    tf_attempts_used = models.PositiveIntegerField(default=0)

    description = models.TextField(blank=True, null=True)
    
    # Subscription status and audit trail
    payement_status = models.CharField(
        max_length=50, 
        choices=SUBSCRIPTION_STATUS, 
        default='pending'
    )
    notes = models.TextField(blank=True, null=True)
    
    # Audit trail fields
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='approved_subscriptions'
    )
    approved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['payement_status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['student', 'payement_status']),
            models.Index(fields=['student', 'feature']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['approved_by']),
        ]
        ordering = ['-created_at']
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"

    def __str__(self):
        return f"{self.student} - {self.feature} - {self.payement_status}"

    def clean(self):
        """Validate subscription data"""
        # Use hasattr to check if student is set without triggering the exception
        if not hasattr(self, 'student') or self.student is None:
            # Student will be set in form.save(), skip validation for now
            return
            
        if self.planning_date_to_start and self.planning_date_to_start < date.today():
            raise ValidationError("Planning start date cannot be in the past")
        
        # Now we can safely check payment validation
        if self.payment:
            if self.payment.student != self.student:
                raise ValidationError("Payment must belong to the same student")
            
            if self.payment.payement_status != 'approved':
                raise ValidationError("Cannot create subscription with unapproved payment")

    def save(self, *args, **kwargs):
        """Override save to handle dates and audit trail"""
        is_new = self.pk is None
        
        # Set start_date if subscription is approved
        if self.payement_status == 'approved' and not self.start_date:
            self.start_date = self.planning_date_to_start or date.today()
            
            # Calculate expiration date
            if self.feature and self.start_date:
                self.expires_at = self.start_date + timedelta(
                    days=self.feature.validity_day_number
                )
        
        # Set approved_at timestamp when status changes to approved
        if not is_new and self.payement_status == 'approved':
            try:
                original = Subscription.objects.get(pk=self.pk)
                if original.payement_status != 'approved' and not self.approved_at:
                    self.approved_at = timezone.now()
            except Subscription.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)

    def calculate_days_available(self):
        """Calculate number of days available in the subscription"""
        if not self.expires_at or not self.start_date:
            return 0
        
        today = date.today()
        
        # If not started yet
        if today < self.start_date:
            return self.feature.validity_day_number
        
        # If active
        if self.start_date <= today <= self.expires_at:
            return (self.expires_at - today).days
        
        # If expired
        return 0

    def get_subscription_status(self):
        """Get current subscription status based on dates"""
        if self.payement_status != 'approved':
            return self.payement_status
        
        if not self.expires_at or not self.start_date:
            return 'pending'
        
        today = date.today()
        
        if today < self.start_date:
            return 'approved'  # Approved but not yet started
        elif self.start_date <= today <= self.expires_at:
            return 'active'
        else:
            return 'expired'

    def get_payement_status_display(self):
        """Get human-readable payment status"""
        status_dict = dict(self.SUBSCRIPTION_STATUS)
        return status_dict.get(self.payement_status, self.payement_status)

    def get_subscription_status_display(self):
        """Get human-readable display for subscription status"""
        status = self.get_subscription_status()
        status_map = {
            'pending': 'En attente',
            'approved': 'Approuvé',
            'rejected': 'Refusé',
            'expired': 'Expiré',
            'active': 'Actif',
        }
        return status_map.get(status, status)

    def can_access_feature(self, feature_code):
        """Check if student can access a specific feature"""
        if self.get_subscription_status() != 'active':
            return False
        
        # Map feature codes to model fields
        feature_map = {
            'add_resume': 'can_add_resume',
            'add_notes': 'can_add_notes',
            'view_terminology': 'can_view_terminology',
            'practice_terminology': 'can_practice_terminology',
            'view_quizlet': 'can_view_quizlet',
            'practice_quizlet': 'can_practice_quizlet_learning_mode',
            'view_image_quiz': 'can_view_image_quiz',
            'practice_image_quiz': 'can_practice_image_quiz',
            'ask_question': 'can_ask_question',
            'view_discussion': 'can_view_dicussion',
            'can_add_own_terminology': 'can_add_own_terminology',
            'can_add_own_flashcard': 'can_add_own_flashcard',

        }
        
        if feature_code not in feature_map:
            return False
        
        return getattr(self.feature, feature_map[feature_code], False)

    def record_mcq_attempt(self):
        """Record a quiz attempt"""
        if self.get_subscription_status() != 'active':
            raise ValidationError("Subscription is not active")
        
        if self.mcq_attempts_used >= self.feature.mcq_features:
            raise ValidationError("Quiz attempt limit reached")
        
        self.mcq_attempts_used += 1
        self.save()

    def record_qa_attempt(self):
        """Record a quiz attempt"""
        if self.get_subscription_status() != 'active':
            raise ValidationError("Subscription is not active")
        
        if self.qa_attempts_used >= self.feature.qa_features:
            raise ValidationError("Quiz attempt limit reached")
        
        self.qa_attempts_used += 1
        self.save()

    def record_tf_attempt(self):
        """Record a quiz attempt"""
        if self.get_subscription_status() != 'active':
            raise ValidationError("Subscription is not active")
        
        if self.tf_attempts_used >= self.feature.tf_features:
            raise ValidationError("Quiz attempt limit reached")
        
        self.tf_attempts_used += 1
        self.save()

    def record_mcq_exam_attempt(self):
        """Record an exam attempt"""
        if self.get_subscription_status() != 'active':
            raise ValidationError("Subscription is not active")
        
        if self.mcq_exam_attempts_used >= self.feature.mcq_exam_feature:
            raise ValidationError("Exam attempt limit reached")
        
        self.mcq_exam_attempts_used += 1
        self.save()

    def record_qa_exam_attempt(self):
        """Record an exam attempt"""
        if self.get_subscription_status() != 'active':
            raise ValidationError("Subscription is not active")
        
        if self.qa_exam_attempts_used >= self.feature.qa_exam_feature:
            raise ValidationError("Exam attempt limit reached")
        
        self.qa_exam_attempts_used += 1
        self.save()

    def get_remaining_mcq(self):
        """Get remaining quiz attempts"""
        if not self.feature:
            return 0
        return max(0, self.feature.mcq_features - self.mcq_attempts_used)
    
    def get_remaining_qa(self):
        """Get remaining quiz attempts"""
        if not self.feature:
            return 0
        return max(0, self.feature.qa_features - self.qa_attempts_used)
    
    def get_remaining_tf(self):
        """Get remaining quiz attempts"""
        if not self.feature:
            return 0
        return max(0, self.feature.tf_features - self.tf_attempts_used)

    def get_remaining_mcq_exams(self):
        """Get remaining exam attempts"""
        if not self.feature:
            return 0
        return max(0, self.feature.mcq_exam_feature - self.mcq_exam_attempts_used)

    def get_remaining_qa_exams(self):
        """Get remaining exam attempts"""
        if not self.feature:
            return 0
        return max(0, self.feature.qa_exam_feature - self.qa_exam_attempts_used)

    def approve_subscription(self, approved_by_user, notes=None):
        """Approve a pending subscription with audit trail"""
        if self.payement_status != 'pending':
            raise ValidationError(f"Subscription is already {self.payement_status}")
        
        if not approved_by_user:
            raise ValidationError("Approving user is required")
        
        self.payement_status = 'approved'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        
        # Set start and expiration dates
        self.start_date = self.planning_date_to_start or date.today()
        if self.feature and self.start_date:
            self.expires_at = self.start_date + timedelta(
                days=self.feature.validity_day_number
            )
        
        if notes:
            self.notes = notes
        
        self.save()
        return self

    def reject_subscription(self, approved_by_user, reason):
        """Reject a pending subscription with audit trail"""
        if self.payement_status != 'pending':
            raise ValidationError(f"Subscription is already {self.payement_status}")
        
        if not approved_by_user:
            raise ValidationError("Rejecting user is required")
        
        self.payement_status = 'rejected'
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.notes = reason
        
        self.save()
        return self

    def is_feature_available(self, feature_name):
        """Check if a specific feature is available in this subscription"""
        feature_methods = {
            'can_add_resume': self.feature.can_add_resume,
            'can_add_notes': self.feature.can_add_notes,
            'can_view_terminology': self.feature.can_view_terminology,
            'can_practice_terminology': self.feature.can_practice_terminology,
            'can_view_quizlet': self.feature.can_view_public_flashcard,
            'can_practice_quizlet_learning_mode': self.feature.can_practice_quizlet_learning_mode,
            'can_view_image_quiz': self.feature.can_view_image_quiz,
            'can_practice_image_quiz': self.feature.can_practice_image_quiz,
            'can_ask_question': self.feature.can_ask_question,
            'can_view_discussion': self.feature.can_view_dicussion,
            'can_add_own_terminology': self.feature.can_add_own_terminology,
            'can_add_own_flashcard': self.feature.can_add_own_flashcard,
        }
        
        return feature_methods.get(feature_name, False)

    def get_audit_info(self):
        """Get audit information for this subscription"""
        audit_info = {
            'status': self.payement_status,
            'status_display': self.get_payement_status_display(),
            'current_status': self.get_subscription_status(),
            'current_status_display': self.get_subscription_status_display(),
            'notes': self.notes,
            'days_available': self.calculate_days_available(),
            'remaining_mcq': self.get_remaining_mcq(),
            'remaining_qa': self.get_remaining_qa(),
            'remaining_tf': self.get_remaining_tf(),
            'remaining_mcq_exams': self.get_remaining_mcq_exams(),
            'remaining_qa_exams': self.get_remaining_qa_exams(),
        }
        
        if self.approved_by:
            audit_info.update({
                'reviewed_by': self.approved_by.get_full_name() or self.approved_by.username,
                'reviewed_at': self.approved_at.strftime('%Y-%m-%d %H:%M:%S') if self.approved_at else 'N/A',
            })
        else:
            audit_info.update({
                'reviewed_by': 'Not yet reviewed',
                'reviewed_at': 'N/A',
            })
        
        return audit_info

    @classmethod
    def get_active_subscriptions(cls, student=None):
        """Get all active subscriptions"""
        queryset = cls.objects.filter(payement_status='approved')
        
        if student:
            queryset = queryset.filter(student=student)
        
        # Filter by date logic
        today = date.today()
        queryset = queryset.filter(
            Q(start_date__lte=today) & Q(expires_at__gte=today)
        )
        
        return queryset

    @classmethod
    def get_student_active_subscription(cls, student):
        """Get active subscription for a specific student"""
        try:
            subscriptions = cls.get_active_subscriptions(student)
            return subscriptions.latest('created_at')
        except cls.DoesNotExist:
            return None
 
    @classmethod
    def get_expiring_soon(cls, days=7):
        """Get subscriptions expiring soon"""
        today = date.today()
        expiration_date = today + timedelta(days=days)
        
        return cls.objects.filter(
            payement_status='approved',
            expires_at__range=[today, expiration_date],
            start_date__lte=today
        ).order_by('expires_at')

    @classmethod
    def get_reviewed_by_user(cls, user):
        """Get all subscriptions reviewed by a specific user"""
        return cls.objects.filter(approved_by=user).exclude(payement_status='pending')


# ========== SUBSCRIPTION USAGE AUDIT ==========
class SubscriptionUsageAudit(models.Model):
    """Audit trail for subscription usage"""
    
    class Meta:
        indexes = [
            models.Index(fields=['subscription', 'action_type']),
            models.Index(fields=['action_at']),
            models.Index(fields=['student']),
        ]
        ordering = ['-action_at']
        verbose_name = "Usage Audit"
        verbose_name_plural = "Usage Audits"

    ACTION_TYPES = [
        ('payment_created', 'Payment Created'),
        ('payment_reviewed', 'Payment Reviewed'),
        ('subscription_created', 'Subscription Created'),
        ('subscription_reviewed', 'Subscription Reviewed'),
        ('quiz_start', 'Quiz Started'),
        ('quiz_complete', 'Quiz Completed'),
        ('exam_start', 'Exam Started'),
        ('exam_complete', 'Exam Completed'),
        ('feature_access', 'Feature Accessed'),
        ('subscription_start', 'Subscription Started'),
        ('subscription_end', 'Subscription Ended'),
    ]

    # Make subscription nullable for payment-related audits
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.CASCADE,
        null=True,  # Allow null
        blank=True   # Allow blank in forms
    )
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    action_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.action_type} - {self.action_at}"

    def get_action_type_display(self):
        """Get human-readable action type"""
        action_dict = dict(self.ACTION_TYPES)
        return action_dict.get(self.action_type, self.action_type)

    @classmethod
    def log_usage(cls, action_type, details=None, request=None, subscription=None, student=None):
        """Log usage - works for both payments and subscriptions"""
        
        # Determine student
        if subscription:
            student_obj = subscription.student
        elif student:
            student_obj = student
        else:
            raise ValueError("Either subscription or student must be provided")
        
        # Ensure JSON serializable details
        serializable_details = {}
        if details:
            for key, value in details.items():
                if hasattr(value, 'isoformat'):
                    serializable_details[key] = value.isoformat()
                else:
                    serializable_details[key] = value
        
        audit = cls(
            subscription=subscription,
            student=student_obj,
            action_type=action_type,
            details=serializable_details
        )
        
        if request:
            audit.ip_address = request.META.get('REMOTE_ADDR')
            audit.user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        audit.save()
        return audit
    
