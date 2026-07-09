# utilisateur/urls_admin.py - FICHIER COMPLET
from django.urls import path
from . import views_admin

app_name = 'admin-user'

urlpatterns = [
    # ======================
    # TABLEAU DE BORD
    # ======================
    path('', views_admin.admin_dashboard, name='dashboard'),
    
    # ======================
    # GESTION DES UTILISATEURS
    # ======================
    path('users/', views_admin.admin_users, name='users'),
    path('users/<int:user_id>/', views_admin.admin_user_detail, name='user_detail'),
    path('users/<int:user_id>/update/', views_admin.admin_user_update, name='user_update'),
    path('users/add/', views_admin.admin_add_user, name='add_user'),
    path('users/<int:user_id>/deactivate/', views_admin.admin_user_deactivate, name='user_deactivate'),
    path('users/<int:user_id>/activate/', views_admin.admin_user_activate, name='user_activate'),
    path('users/<int:user_id>/delete/', views_admin.admin_user_delete, name='user_delete'),
    path('users/<int:user_id>/revoke-premium/', views_admin.admin_user_revoke_premium, name='revoke_premium'),
    path('users/send-message/', views_admin.admin_send_user_message, name='send_user_message'),
    path('users/export/', views_admin.admin_export_users, name='export_users'),
    
    # ======================
    # GESTION DES ÉTUDIANTS
    # ======================
    path('students/', views_admin.admin_students, name='students'),
    
    # ======================
    # JOURNAUX D'ACTIVITÉ
    # ======================
    path('activity-logs/', views_admin.admin_activity_logs, name='activity_logs'),
    path('activity-logs/<int:activity_id>/details/', views_admin.admin_activity_details, name='activity_details'),
    path('activity-logs/export/', views_admin.admin_export_activity_logs, name='export_activity_logs'),
    path('activity-logs/clear-old/', views_admin.admin_clear_old_logs, name='clear_old_logs'),
    
    # ======================
    # NOTIFICATIONS
    # ======================
    path('send-notification/', views_admin.admin_send_notification, name='send_notification'),
    path('notification-stats/', views_admin.admin_notification_stats, name='notification_stats'),
    
    # ======================
    # STATISTIQUES ET API
    # ======================
    path('quick-stats/', views_admin.admin_quick_stats, name='quick_stats'),
    
    # ======================
    # SYSTÈME (SUPERUSER ONLY)
    # ======================
    path('system/status/', views_admin.admin_system_status, name='system_status'),
    path('system/refresh-status/', views_admin.admin_refresh_system_status, name='refresh_system_status'),
    path('system/test-database/', views_admin.admin_test_database, name='test_database'),
    path('system/database-info/', views_admin.admin_database_info, name='database_info'),
    path('system/database-optimize/', views_admin.admin_database_optimize, name='database_optimize_all'),
    path('system/database-optimize/<str:table_name>/', views_admin.admin_database_optimize, name='database_optimize'),
    path('system/database-backup/', views_admin.admin_database_backup, name='database_backup'),
    path('system/cache-clear/', views_admin.admin_cache_clear, name='cache_clear'),
    path('system/migrate/', views_admin.admin_system_migrate, name='system_migrate'),
    path('system/collectstatic/', views_admin.admin_collect_static, name='collect_static'),
    path('system/restart/', views_admin.admin_system_restart, name='system_restart'),
    path('system/toggle-maintenance/', views_admin.admin_toggle_maintenance, name='toggle_maintenance'),
    path('system/send-test-email/', views_admin.admin_send_test_email, name='send_test_email'),
    
    # ======================
    # GESTION DES PERMISSIONS
    # ======================
    path('system/permissions/', views_admin.admin_permission_manager, name='permission_manager'),
    path('system/permissions/create-group/', views_admin.admin_create_group, name='create_group'),
    path('system/permissions/refresh/', views_admin.admin_refresh_permissions, name='refresh_permissions'),
]