# users/urls.py
from django.urls import path
from . import views

app_name = 'utilisateur'

urlpatterns = [
    path('', views.premier_page, name='premier-page'),
    # ===== Authentication =====
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    
    # ===== Dashboard & Profile =====
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/delete-picture/', views.delete_profile_picture, name='delete_profile_picture'),

    # Settings
    path('settings/', views.SettingsView.as_view(), name='settings'),
    path('notifications/', views.NotificationView.as_view(), name='notifications'),
    
    # Password Management
    path('password/change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password/reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]

urlpatterns += [
    # Profile picture management
    path('profile/picture/upload-ajax/', views.ajax_upload_profile_picture, name='ajax_upload_profile_picture'),
    path('profile/picture/urls/', views.get_profile_picture_urls, name='get_profile_picture_urls'),
    path('profile/picture/set-active/', views.set_active_profile_picture_view, name='set_active_profile_picture'),
    path('profile/completion/', views.get_profile_completion, name='get_profile_completion'),
    
    # Session management
    path('sessions/logout-other/', views.logout_other_sessions, name='logout_other_sessions'),
]

urlpatterns += [
    # Profile URLs
    path('profile/', views.profile_view, name='profile'),
    path('profile/update/', views.profile_update, name='profile_update'),
    path('profile/update/<str:role>/', views.role_profile_update, name='role_profile_update'),
    path('profile/update-picture/', views.update_profile_pic, name='update_profile_pic'),
    path('profile/delete-picture/', views.delete_profile_pic, name='delete_profile_pic'),
    path('profile/stats/', views.profile_stats, name='profile_stats'),

    # list de mambre pour interaction
    path('member/', views.list_membres, name="member"),
    path('member/user/<int:user_id>/', views.voir_profil, name="voir_profil"),
]