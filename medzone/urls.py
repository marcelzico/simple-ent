"""
URL configuration for medzone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Password reset URLs at project level
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='utilisateur/password_change.html',
        success_url='/password-change/done/'
    ), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='utilisateur/password_change_done.html'
    ), name='password_change_done'),
    
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='utilisateur/password_reset.html',
        email_template_name='utilisateur/password_reset_email.html',
        subject_template_name='utilisateur/password_reset_subject.txt',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='utilisateur/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='utilisateur/password_reset_confirm.html',
        success_url='/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='utilisateur/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # # Include utilisateur app URLs
    path('', include('utilisateur.urls')),
    
    # # Other app includes
    path('leçon/', include('lecon.urls')),
    path('quiz/', include('quizzes.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('note/', include('lessoncopy.urls', namespace='lessoncopy')),
    path('subscription/', include('subscriptions.urls')),
    path('student/', include('student.urls')),
    # path('teacher/', include('teacher.urls')),
    # Include bulk_import app URLs
    path('bulk-import/', include('bulk_import.urls', namespace='bulk_import')),


]

# Serve media files in development only
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Also serve static files during development
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
