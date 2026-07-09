# subscriptions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.utils import timezone
from datetime import date, timedelta

from .models import Payment, Subscription, Feature, SubscriptionUsageAudit
from .forms import (
    PaymentForm, StudentSubscriptionForm, 
    AdminPaymentForm, AdminSubscriptionForm, FeatureForm
)
from student.models import StudentProfile


# ========== HELPER FUNCTIONS ==========
def is_student(user):
    """Check if user is a student"""
    return hasattr(user, 'studentprofile') and not user.is_staff

def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_staff

# subscriptions/views.py - Make sure get_student_profile is working

def get_student_profile(user):
    """Get student profile for authenticated user"""
    try:
        # Check if user has studentprofile directly
        if hasattr(user, 'student_profile'):
            return user.student_profile
        
        # Or try to get it through StudentProfile model
        from student.models import StudentProfile
        return StudentProfile.objects.get(user=user)
    except StudentProfile.DoesNotExist:
        return None
    except Exception as e:
        print(f"Error getting student profile: {e}")
        return None


# ========== STUDENT VIEWS ==========

class StudentDashboardView(LoginRequiredMixin, View):
    """Student dashboard showing active subscription and features"""
    
    def get(self, request):
        student = get_student_profile(request.user)
        if not student:
            messages.error(request, "Student profile not found")
            return redirect('subscriptions:dashboard')
        
        # Get active subscription
        active_subscription = Subscription.get_student_active_subscription(student)
        
        # Get recent payments
        recent_payments = Payment.get_student_payments(student)[:5]
        
        # Get subscription history
        subscription_history = Subscription.objects.filter(
            student=student
        ).order_by('-created_at')[:10]
        
        # Get available features
        available_features = Feature.objects.all().order_by('price')
        
        context = {
            'student': student,
            'active_subscription': active_subscription,
            'recent_payments': recent_payments,
            'subscription_history': subscription_history,
            'available_features': available_features,
        }
        
        return render(request, 'subscriptions/student_dashboard.html', context)


class CreatePaymentView(LoginRequiredMixin, View):
    """View for students to create payment requests"""
    
    def get(self, request):
        student = get_student_profile(request.user)
        if not student:
            messages.error(request, "Student profile not found")
            return redirect('subscriptions:admin_dashboard') 
        
        # Get feature from query parameter if provided
        feature_id = request.GET.get('feature')
        initial_data = {}
        if feature_id:
            try:
                feature = Feature.objects.get(id=feature_id)
                initial_data['feature'] = feature
                initial_data['amount'] = feature.price
            except Feature.DoesNotExist:
                pass
        
        form = PaymentForm(student=student, initial=initial_data)
        features = Feature.objects.all().order_by('price')
        
        return render(request, 'subscriptions/create_payment.html', {
            'form': form,
            'features': features,
            'student': student,
        })
    
    def post(self, request):
        student = get_student_profile(request.user)
        if not student:
            messages.error(request, "Student profile not found")
            return redirect('subscriptions:dashboard')
        
        form = PaymentForm(request.POST, student=student)
        
        if form.is_valid():
            payment = form.save()
            
            # Create payment success message
            messages.success(
                request,
                f"Payment request submitted successfully! "
                f"Reference: {payment.reference_of_payment}. "
                f"Please wait for admin verification."
            )

            SubscriptionUsageAudit.log_usage(
                action_type='payment_created',
                details={
                    'payment_id': payment.id,
                    'amount': payment.amount,
                    'feature': payment.feature.name if payment.feature else None,
                },
                request=request,
                student=student  # Pass student directly for payment creation
            )
                        
            return redirect('subscriptions:student_dashboard')
        
        features = Feature.objects.all().order_by('price')
        return render(request, 'subscriptions/create_payment.html', {
            'form': form,
            'features': features,
            'student': student,
        })
    

class CreateSubscriptionView(LoginRequiredMixin, View):
    """View for students to create subscription requests"""

    def get(self, request):
        student = get_student_profile(request.user)
        if not student:
            messages.error(request, "Student profile not found")
            return redirect('subscriptions:dashboard')
        
        # Check if student has approved payments
        approved_payments = Payment.objects.filter(
            student=student,
            payement_status='approved'
        )
        
        if not approved_payments.exists():
            messages.warning(
                request,
                "You need to have an approved payment before creating a subscription. "
                "Please make a payment first."
            )
            return redirect('subscriptions:create_payment')
        
        form = StudentSubscriptionForm(student=student, user=request.user)
        
        return render(request, 'subscriptions/create_subscription.html', {
            'form': form,
            'student': student,
            'approved_payments': approved_payments,
        })
    
    # In CreateSubscriptionView.post()
    def post(self, request):
        student = get_student_profile(request.user)
        print(f"Student from get_student_profile: {student}")  # Debug
        print(f"User: {request.user}")  # Debug
        print(f"User has studentprofile: {hasattr(request.user, 'studentprofile')}")  # Debug
        
        if not student:
            messages.error(request, "Student profile not found")
            return redirect('home')
        
        form = StudentSubscriptionForm(request.POST, student=student, user=request.user)
        print(f"Form data: {request.POST}")  # Debug
        
        if form.is_valid():
            subscription = form.save()
            
            messages.success(
                request,
                f"Subscription request submitted successfully! "
                f"You'll be notified when it's reviewed by admin."
            )

            SubscriptionUsageAudit.log_usage(
                action_type='subscription_created',
                details={
                    'feature': subscription.feature.name,
                    'planning_date': str(subscription.planning_date_to_start) if subscription.planning_date_to_start else None,
                },
                request=request,
                subscription=subscription  # Pass subscription for subscription creation
            )
                                
            return redirect('subscriptions:student_dashboard')
        else:
            print(f"Form errors: {form.errors}")  # Debug
            print(f"Form non-field errors: {form.non_field_errors}")  # Debug
    
        approved_payments = Payment.objects.filter(
            student=student,
            payement_status='approved'
        )

    
        return render(request, 'subscriptions/create_subscription.html', {
            'form': form,
            'student': student,
            'approved_payments': approved_payments,
        })


class StudentPaymentListView(LoginRequiredMixin, ListView):
    """View for students to see their payment history"""
    model = Payment
    template_name = 'subscriptions/student_payment_list.html'
    context_object_name = 'payments'
    paginate_by = 10
    
    def get_queryset(self):
        student = get_student_profile(self.request.user)
        if student:
            return Payment.get_student_payments(student)
        return Payment.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_student_profile(self.request.user)
        return context


class StudentSubscriptionListView(LoginRequiredMixin, ListView):
    """View for students to see their subscription history"""
    model = Subscription
    template_name = 'subscriptions/student_subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 10
    
    def get_queryset(self):
        student = get_student_profile(self.request.user)
        if student:
            return Subscription.objects.filter(student=student).order_by('-created_at')
        return Subscription.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['student'] = get_student_profile(self.request.user)
        return context


class SubscriptionDetailView(LoginRequiredMixin, DetailView):
    """View for students to see subscription details"""
    model = Subscription
    template_name = 'subscriptions/subscription_detail.html'
    context_object_name = 'subscription'
    
    def get_queryset(self):
        student = get_student_profile(self.request.user)
        if student:
            return Subscription.objects.filter(student=student)
        return Subscription.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = self.get_object()
        context['student'] = get_student_profile(self.request.user)
        context['audit_info'] = subscription.get_audit_info()
        context['can_see_notes'] = subscription.payement_status in ['approved', 'rejected']
        
        # Add quiz usage details
        if subscription.feature:
            context['quiz_limits'] = {
                'mcq': {
                    'total': subscription.feature.mcq_features,
                    'used': subscription.mcq_attempts_used,
                    'remaining': subscription.get_remaining_mcq()
                },
                'mcq_exam': {
                    'total': subscription.feature.mcq_exam_feature,
                    'used': subscription.mcq_exam_attempts_used,
                    'remaining': subscription.get_remaining_mcq_exams()
                },
                'qa': {
                    'total': subscription.feature.qa_features,
                    'used': subscription.qa_attempts_used,
                    'remaining': subscription.get_remaining_qa()
                },
                'qa_exam': {
                    'total': subscription.feature.qa_exam_feature,
                    'used': subscription.qa_exam_attempts_used,
                    'remaining': subscription.get_remaining_qa_exams()
                },
                'tf': {
                    'total': subscription.feature.tf_features,
                    'used': subscription.tf_attempts_used,
                    'remaining': subscription.get_remaining_tf()
                }
            }
        
        return context


# ========== ADMIN VIEWS ==========

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Admin dashboard for managing payments and subscriptions"""
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get(self, request):
        # Get pending payments and subscriptions
        pending_payments = Payment.get_pending_payments()
        pending_subscriptions = Subscription.objects.filter(
            payement_status='pending'
        ).order_by('-created_at')
        
        # Get recent approved items
        recent_approved_payments = Payment.objects.filter(
            payement_status='approved'
        ).order_by('-approved_at')[:10]
        
        recent_approved_subscriptions = Subscription.objects.filter(
            payement_status='approved'
        ).order_by('-approved_at')[:10]
        
        # Get expiring subscriptions
        expiring_subscriptions = Subscription.get_expiring_soon(days=7)
        
        # Get statistics
        total_payments = Payment.objects.count()
        total_approved_payments = Payment.objects.filter(payement_status='approved').count()
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.get_active_subscriptions().count()
        
        context = {
            'pending_payments': pending_payments,
            'pending_subscriptions': pending_subscriptions,
            'recent_approved_payments': recent_approved_payments,
            'recent_approved_subscriptions': recent_approved_subscriptions,
            'expiring_subscriptions': expiring_subscriptions,
            'stats': {
                'total_payments': total_payments,
                'approved_payments': total_approved_payments,
                'total_subscriptions': total_subscriptions,
                'active_subscriptions': active_subscriptions,
            }
        }
        
        return render(request, 'subscriptions/admin_dashboard.html', context)


class AdminPaymentReviewView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for admin to review payments"""
    model = Payment
    form_class = AdminPaymentForm
    template_name = 'subscriptions/admin_payment_review.html'
    context_object_name = 'payment'
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        payment = form.save()
        
        # Create appropriate message
        if payment.payement_status == 'approved':
            messages.success(
                self.request,
                f"Payment approved successfully for {payment.student}"
            )
        else:
            messages.warning(
                self.request,
                f"Payment rejected for {payment.student}"
            )
        
        # Log the review action
        SubscriptionUsageAudit.log_usage(
            action_type='payment_reviewed',
            details={
                'payment_id': payment.id,
                'status': payment.payement_status,
                'reviewed_by': self.request.user.username,
            },
            request=self.request,
            student=payment.student  # Pass student from payment
        )
        
        return redirect('subscriptions:admin_dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment'] = self.get_object()
        return context


class AdminSubscriptionReviewView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for admin to review subscriptions"""
    model = Subscription
    form_class = AdminSubscriptionForm
    template_name = 'subscriptions/admin_subscription_review.html'
    context_object_name = 'subscription'
    
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        subscription = form.save()
        
        # Create appropriate message
        if subscription.payement_status == 'approved':
            messages.success(
                self.request,
                f"Subscription approved successfully for {subscription.student}"
            )
        else:
            messages.warning(
                self.request,
                f"Subscription rejected for {subscription.student}"
            )
        
        # Log the review action
        SubscriptionUsageAudit.log_usage(
            action_type='subscription_reviewed',
            details={
                'status': subscription.payement_status,
                'reviewed_by': self.request.user.username,
            },
            request=self.request,
            subscription=subscription  # Pass subscription
        )
        
        return redirect('subscriptions:admin_dashboard')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subscription = self.get_object()
        context['subscription'] = subscription
        context['audit_info'] = subscription.get_audit_info()
        return context


class PaymentListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to list all payments"""
    model = Payment
    template_name = 'subscriptions/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 20
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_queryset(self):
        queryset = Payment.objects.all().order_by('-created_at')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(payement_status=status)
        
        # Filter by student if provided
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['student_filter'] = self.request.GET.get('student', '')
        return context


class SubscriptionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to list all subscriptions"""
    model = Subscription
    template_name = 'subscriptions/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 20
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_queryset(self):
        queryset = Subscription.objects.all().order_by('-created_at')
        
        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            if status == 'active':
                queryset = Subscription.get_active_subscriptions()
            else:
                queryset = queryset.filter(payement_status=status)
        
        # Filter by student if provided
        student_id = self.request.GET.get('student')
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['student_filter'] = self.request.GET.get('student', '')
        return context


class FeatureManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to manage features"""
    model = Feature
    template_name = 'subscriptions/feature_management.html'
    context_object_name = 'features'
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = FeatureForm()
        return context


class CreateFeatureView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """View for admin to create new features"""
    model = Feature
    form_class = FeatureForm
    template_name = 'subscriptions/feature_form.html'
    success_url = reverse_lazy('feature_management')
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Feature created successfully!")
        return super().form_valid(form)


class UpdateFeatureView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View for admin to update features"""
    model = Feature
    form_class = FeatureForm
    template_name = 'subscriptions/feature_form.html'
    success_url = reverse_lazy('feature_management')
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Feature updated successfully!")
        return super().form_valid(form)


class UsageAuditView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin view to see usage audit logs"""
    model = SubscriptionUsageAudit
    template_name = 'subscriptions/usage_audit.html'
    context_object_name = 'audit_logs'
    paginate_by = 50
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def get_queryset(self):
        queryset = SubscriptionUsageAudit.objects.all().order_by('-action_at')
        
        # Filter by subscription if provided
        subscription_id = self.request.GET.get('subscription')
        if subscription_id:
            queryset = queryset.filter(subscription_id=subscription_id)
        
        # Filter by action type if provided
        action_type = self.request.GET.get('action_type')
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        
        # Filter by date range if provided
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(action_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(action_at__date__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subscription_filter'] = self.request.GET.get('subscription', '')
        context['action_type_filter'] = self.request.GET.get('action_type', '')
        context['date_from_filter'] = self.request.GET.get('date_from', '')
        context['date_to_filter'] = self.request.GET.get('date_to', '')
        return context