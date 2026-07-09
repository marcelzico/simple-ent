# subscription/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Payment, Subscription, Feature, SubscriptionUsageAudit


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'feature', 'amount', 'paid_with', 
        'payement_status_display', 'approved_by', 'created_at', 'review_link'
    ]
    list_filter = ['payement_status', 'paid_with', 'created_at', 'approved_at']
    search_fields = ['student__user__username', 'student__user__email', 'reference_of_payment']
    readonly_fields = ['created_at', 'approved_at']
    fieldsets = (
        ('Payment Information', {
            'fields': ('student', 'feature', 'amount', 'paid_with')
        }),
        ('Transaction Details', {
            'fields': ('phone_number_of_payment', 'reference_of_payment', 'description')
        }),
        ('Status & Review', {
            'fields': ('payement_status', 'notes', 'approved_by', 'approved_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def payement_status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
        }
        color = status_colors.get(obj.payement_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_payement_status_display()
        )
    payement_status_display.short_description = 'Status'
    
    def review_link(self, obj):
        if obj.payement_status == 'pending':
            return format_html(
                '<a href="{}" class="button">Review</a>',
                reverse('subscriptions:admin_payment_review', args=[obj.pk])
            )
        return '-'
    review_link.short_description = 'Actions'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs
    
    def has_change_permission(self, request, obj=None):
        if obj and obj.payement_status != 'pending' and not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)
    
    def save_model(self, request, obj, form, change):
        if obj.payement_status != 'pending' and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


class FeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'price', 'validity_day_number', 
                    'mcq_features', 'qa_features', 'tf_features',
                    'mcq_exam_feature', 'qa_exam_feature']
    list_filter = ['price', 'validity_day_number']
    search_fields = ['name', 'code']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'code', 'price', 'validity_day_number')
        }),
        ('Usage Limits - MCQs', {
            'fields': ('mcq_features', 'mcq_exam_feature'),
            'classes': ('collapse',)
        }),
        ('Usage Limits - Q&A', {
            'fields': ('qa_features', 'qa_exam_feature'),
            'classes': ('collapse',)
        }),
        ('Usage Limits - True/False', {
            'fields': ('tf_features',),
            'classes': ('collapse',)
        }),
        ('Feature Flags', {
            'fields': (
                'can_add_resume', 'can_add_notes',
                'can_view_terminology', 'can_practice_terminology', 'can_add_own_terminology',
                'can_view_public_flashcard', 'can_add_own_flashcard', 'can_practice_quizlet_learning_mode',
                'can_view_image_quiz', 'can_practice_image_quiz',
                'can_ask_question', 'can_view_dicussion'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'feature', 'amount', 'payement_status_display',
        'current_status', 'days_remaining', 'approved_by', 'created_at', 'subscription_review_link'
    ]
    list_filter = ['payement_status', 'created_at', 'approved_at', 'feature']
    search_fields = ['student__user__username', 'student__user__email']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    fieldsets = (
        ('Subscription Information', {
            'fields': ('student', 'payment', 'feature', 'amount')
        }),
        ('Subscription Dates', {
            'fields': ('planning_date_to_start', 'start_date', 'expires_at')
        }),
        ('Usage Tracking - MCQs', {
            'fields': ('mcq_attempts_used', 'mcq_exam_attempts_used'),
            'classes': ('collapse',)
        }),
        ('Usage Tracking - Q&A', {
            'fields': ('qa_attempts_used', 'qa_exam_attempts_used'),
            'classes': ('collapse',)
        }),
        ('Usage Tracking - True/False', {
            'fields': ('tf_attempts_used',),
            'classes': ('collapse',)
        }),
        ('Status & Review', {
            'fields': ('payement_status', 'notes', 'approved_by', 'approved_at')
        }),
        ('Additional Information', {
            'fields': ('description',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
        
    def payement_status_display(self, obj):
        status_colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'active': 'blue',
            'expired': 'gray',
        }
        color = status_colors.get(obj.payement_status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_payement_status_display()
        )
    payement_status_display.short_description = 'Status'
    
    def current_status(self, obj):
        status = obj.get_subscription_status()
        status_colors = {
            'pending': 'orange',
            'approved': 'green',
            'rejected': 'red',
            'active': 'blue',
            'expired': 'gray',
        }
        color = status_colors.get(status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_subscription_status_display()
        )
    current_status.short_description = 'Current Status'
    
    def days_remaining(self, obj):
        days = obj.calculate_days_available()
        if days > 0:
            color = 'green' if days > 7 else 'orange'
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} days</span>',
                color,
                days
            )
        return '-'
    days_remaining.short_description = 'Days Remaining'
    
    def subscription_review_link(self, obj):
        if obj.payement_status == 'pending':
            return format_html(
                '<a href="{}" class="button">Review</a>',
                reverse('subscriptions:admin_subscription_review', args=[obj.pk])
            )
        return '-'
    subscription_review_link.short_description = 'Actions'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs


class SubscriptionUsageAuditAdmin(admin.ModelAdmin):
    list_display = ['student', 'subscription', 'action_type_display', 'ip_address', 'action_at']
    list_filter = ['action_type', 'action_at']
    search_fields = ['student__user__username', 'subscription__id']
    readonly_fields = ['action_at', 'ip_address', 'user_agent']
    
    def action_type_display(self, obj):
        return obj.get_action_type_display()
    action_type_display.short_description = 'Action Type'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Register all models
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Feature, FeatureAdmin)
admin.site.register(SubscriptionUsageAudit, SubscriptionUsageAuditAdmin)