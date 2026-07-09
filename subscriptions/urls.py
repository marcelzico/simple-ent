# subscription/urls.py
from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    # Student URLs
    path('dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('payment/create/', views.CreatePaymentView.as_view(), name='create_payment'),
    path('subscription/create/', views.CreateSubscriptionView.as_view(), name='create_subscription'),
    path('payments/', views.StudentPaymentListView.as_view(), name='student_payment_list'),
    path('subscriptions/', views.StudentSubscriptionListView.as_view(), name='student_subscription_list'),
    path('subscription/<int:pk>/', views.SubscriptionDetailView.as_view(), name='subscription_detail'),
    
    # Admin URLs
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/payment/<int:pk>/review/', views.AdminPaymentReviewView.as_view(), name='admin_payment_review'),
    path('admin/subscription/<int:pk>/review/', views.AdminSubscriptionReviewView.as_view(), name='admin_subscription_review'),
    path('admin/payments/', views.PaymentListView.as_view(), name='payment_list'),
    path('admin/subscriptions/', views.SubscriptionListView.as_view(), name='subscription_list'),
    path('admin/features/', views.FeatureManagementView.as_view(), name='feature_management'),
    path('admin/feature/create/', views.CreateFeatureView.as_view(), name='create_feature'),
    path('admin/feature/<int:pk>/edit/', views.UpdateFeatureView.as_view(), name='update_feature'),
    path('admin/usage-audit/', views.UsageAuditView.as_view(), name='usage_audit'),
]