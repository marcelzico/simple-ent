# users/management/commands/init_admin_permissions.py - NOUVEAU FICHIER
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from users.models import AdminPermission, AdminDashboardModule

class Command(BaseCommand):
    help = 'Initialiser les permissions et modules administratifs'
    
    def handle(self, *args, **options):
        # Créer les permissions administratives
        permissions_data = [
            ('view_users', 'Voir les utilisateurs'),
            ('manage_users', 'Gérer les utilisateurs'),
            ('view_students', 'Voir les étudiants'),
            ('manage_students', 'Gérer les étudiants'),
            ('view_teachers', 'Voir les enseignants'),
            ('manage_teachers', 'Gérer les enseignants'),
            ('view_enrollments', 'Voir les inscriptions'),
            ('manage_enrollments', 'Gérer les inscriptions'),
            ('view_sessions', 'Voir les sessions'),
            ('manage_sessions', 'Gérer les sessions'),
            ('view_subjects', 'Voir les matières'),
            ('manage_subjects', 'Gérer les matières'),
            ('view_levels', 'Voir les niveaux'),
            ('manage_levels', 'Gérer les niveaux'),
            ('view_reports', 'Voir les rapports'),
            ('manage_reports', 'Gérer les rapports'),
            ('view_finance', 'Voir les finances'),
            ('manage_finance', 'Gérer les finances'),
            ('view_settings', 'Voir les paramètres'),
            ('manage_settings', 'Gérer les paramètres'),
            ('view_analytics', 'Voir les analyses'),
            ('manage_analytics', 'Gérer les analyses'),
            ('send_notifications', 'Envoyer des notifications'),
            ('manage_content', 'Gérer le contenu'),
            ('verify_teachers', 'Vérifier les enseignants'),
            ('approve_premium', 'Approuver les abonnements premium'),
            ('manage_support', 'Gérer le support'),
        ]
        
        for codename, name in permissions_data:
            AdminPermission.objects.get_or_create(
                codename=codename,
                defaults={'name': codename}
            )
        
        # Créer les modules du tableau de bord
        modules_data = [
            ('users', 'Utilisateurs', 'fas fa-users', '#3498db', 'admin:users'),
            ('students', 'Étudiants', 'fas fa-user-graduate', '#2980b9', 'admin:users?role=student'),
            ('teachers', 'Enseignants', 'fas fa-chalkboard-teacher', '#27ae60', 'admin:users?role=teacher'),
            ('enrollments', 'Inscriptions', 'fas fa-book', '#9b59b6', '#'),
            ('sessions', 'Sessions', 'fas fa-calendar-alt', '#e74c3c', '#'),
            ('subjects', 'Matières', 'fas fa-book-open', '#f39c12', '#'),
            ('levels', 'Niveaux', 'fas fa-layer-group', '#1abc9c', '#'),
            ('finance', 'Finances', 'fas fa-money-bill-wave', '#2ecc71', '#'),
            ('reports', 'Rapports', 'fas fa-chart-bar', '#34495e', '#'),
            ('analytics', 'Analyses', 'fas fa-chart-line', '#9b59b6', '#'),
            ('notifications', 'Notifications', 'fas fa-bell', '#e67e22', 'admin:send_notification'),
            ('content', 'Contenu', 'fas fa-file-alt', '#d35400', '#'),
            ('support', 'Support', 'fas fa-headset', '#16a085', '#'),
            ('settings', 'Paramètres', 'fas fa-cogs', '#7f8c8d', '#'),
            ('verification', 'Vérification', 'fas fa-check-circle', '#27ae60', '#'),
        ]
        
        for i, (codename, name, icon, color, url_name) in enumerate(modules_data, 1):
            module, created = AdminDashboardModule.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': codename,
                    'icon': icon,
                    'color': color,
                    'url_name': url_name,
                    'url_pattern': '/',
                    'order': i,
                    'description': f'Gestion des {name.lower()}'
                }
            )
        
        # Créer des groupes par défaut
        groups_data = [
            ('administrateurs', 'Administrateurs complets'),
            ('moderateurs', 'Modérateurs de contenu'),
            ('support', 'Équipe support'),
            ('finances', 'Gestion finances'),
            ('pedagogie', 'Équipe pédagogique'),
        ]
        
        for group_name, group_desc in groups_data:
            Group.objects.get_or_create(
                name=group_name,
                defaults={'name': group_name}
            )
        
        self.stdout.write(self.style.SUCCESS('Permissions et modules administratifs initialisés avec succès!'))