from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.views import View
from django.core.files.storage import FileSystemStorage
import os
from django.http import JsonResponse
from django.contrib.auth.views import (PasswordChangeView, PasswordChangeDoneView,
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView)

from .models import User
from student.models import StudentProfile
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from PIL import Image
import io
from django.core.files.base import ContentFile
from django.contrib.sessions.models import Session
from django.db.models import Avg, Q
from django.utils.decorators import method_decorator
from quizzes.models import MCQResult
from lessoncopy.models import StudySession
from subscriptions.models import Subscription, Feature, Payment
from datetime import datetime, timedelta
import json
from .forms import StudentProfileUpdateForm, UserRegistrationForm, UserProfileForm




def premier_page (request):
    return render (request, "utilisateur/premier-page.html")

# ======================
# AUTHENTICATION VIEWS
# ======================

class LoginView(View):
    """Custom login view"""
    template_name = 'utilisateur/login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('utilisateur:dashboard')
        
        next_url = request.GET.get('next', '')
        return render(request, self.template_name, {'next': next_url})
    
    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        next_url = request.POST.get('next', '')
        
        if not username or not password:
            messages.error(request, "Veuillez saisir votre nom d'utilisateur et mot de passe.")
            return render(request, self.template_name, {'next': next_url})
        
        # Try authentication with username
        user = authenticate(request, username=username, password=password)
        
        # If fails, try with email
        if user is None:
            try:
                user_by_email = User.objects.get(email=username)
                user = authenticate(request, username=user_by_email.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            auth_login(request, user)
            
            # Handle remember me
            if remember_me:
                request.session.set_expiry(2592000)  # 30 days
            else:
                request.session.set_expiry(0)
            
            # Check if student profile exists, create if not
            if user.is_student and not hasattr(user, 'student_profile'):
                from student.models import StudentProfile
                try:
                    StudentProfile.objects.create(user=user)
                    messages.info(request, "Profil étudiant créé. Veuillez le compléter.")
                except Exception as e:
                    messages.warning(request, f"Profil étudiant non créé: {str(e)}")
            
            # NEW: If user is student but profile incomplete, suggest completion
            if user.is_student and hasattr(user, 'student_profile'):
                # Check if profile is minimally complete
                profile = user.student_profile
                if not profile.level or not profile.institution:
                    messages.info(
                        request,
                        "Veuillez compléter votre profil étudiant pour une meilleure expérience."
                    )
                    # Optionally redirect to profile update page
                    # return redirect('utilisateur:profile_update', role='student')
            
            # Check if needs staff/admin access (if applicable)
            # Remove role selection check since we removed that feature
            # if not user.is_student or not user.is_staff or not user.is_superuser:
            #     messages.info(request, "Veuillez sélectionner votre rôle.")
            #     return redirect('utilisateur:role_selection')  # REMOVED
            
            if next_url and next_url != 'None':
                return redirect(next_url)
            
            return redirect('utilisateur:dashboard')
        
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return render(request, self.template_name, {'next': next_url})


class LogoutView(View):
    """Custom logout view"""
    
    def get(self, request):
        messages.info(request, "Vous avez été déconnecté avec succès.")
        auth_logout(request)
        request.session.flush()
        return redirect('utilisateur:login')


class RegisterView(View):
    """User registration view - creates student and redirects to login"""
    template_name = 'utilisateur/register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('utilisateur:dashboard')
        
        form = UserRegistrationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UserRegistrationForm(request.POST)
        
        if form.is_valid():
            # Save the user
            user = form.save(commit=False)
            # Automatically make all new users students
            user.is_student = True
            user.save()
            
            # StudentProfile will be created by the signal
            # Check if it was created or create it manually
            if not hasattr(user, 'student_profile'):
                StudentProfile.objects.create(user=user)
            
            # Show success message
            messages.success(
                request, 
                "Compte étudiant créé avec succès! Veuillez vous connecter."
            )
            
            # Log out the user (so they have to log in)
            auth_logout(request)
            
            # Redirect to login page
            return redirect('utilisateur:login')
        
        return render(request, self.template_name, {'form': form})
    
# ======================
# PROFILE VIEWS
# ======================

@login_required
def dashboard(request):
    """User dashboard"""
    user = request.user
    
    context = {'user': user}
    
    
    if user.is_student and hasattr(user, 'student_profile'):
        context['student_profile'] = user.student_profile
        return redirect('student:dashboard')
    
    if user.is_teacher and hasattr(user, 'teacher_profile'):
        context['teacher_profile'] = user.teacher_profile
        return redirect('teacher:dashboard')
    
    elif user.is_superuser or request.user.is_staff:
        return redirect ('dashboard:dashboard')
    
    else:
        messages.info(request, "Veuillez compléter votre profil.")
        return redirect('utilisateur:login')
    
    return render(request, template, context)


# ======================
# DJANGO BUILT-IN VIEWS (with custom templates)
# ======================

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'utilisateur/password_change.html'
    success_url = reverse_lazy('utilisateur:password_change_done')


class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'utilisateur/password_change_done.html'


class CustomPasswordResetView(PasswordResetView):
    template_name = 'utilisateur/password_reset.html'
    email_template_name = 'utilisateur/password_reset_email.html'
    subject_template_name = 'utilisateur/password_reset_subject.txt'
    success_url = reverse_lazy('utilisateur:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'utilisateur/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'utilisateur/password_reset_confirm.html'
    success_url = reverse_lazy('utilisateur:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'utilisateur/password_reset_complete.html'


class EnhancedDashboardView(LoginRequiredMixin, TemplateView):
    """Enhanced dashboard with stats and recent activity"""
    template_name = 'utilisateur/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['current_date'] = timezone.now()
        
        # Student context
        if user.is_student and hasattr(user, 'student_profile'):
            student_profile = user.student_profile
            enrollments = student_profile.enrollments.filter(is_active=True)
            context['student_enrollments'] = enrollments
            context['student_enrollments_count'] = enrollments.count()
            
            # Calculate completion rate
            completed_courses = enrollments.filter(status='completed').count()
            if enrollments.count() > 0:
                context['completion_rate'] = int((completed_courses / enrollments.count()) * 100)
        
        # Teacher context
        if user.is_teacher and hasattr(user, 'teacher_profile'):
            teacher_profile = user.teacher_profile
            teacher_enrollments = teacher_profile.enrollments.filter(is_active=True)
            context['teacher_students_count'] = teacher_enrollments.count()
        
        # Recent activity simulation
        context['recent_activities'] = self.get_recent_activities(user)
        
        return context
    
    def get_recent_activities(self, user):
        """Generate recent activity feed"""
        activities = []
        
        # Add some example activities
        if user.is_student:
            activities.append({
                'icon': 'book',
                'title': 'Cours terminé',
                'description': 'Vous avez terminé le cours de Mathématiques',
                'time': 'Il y a 2 heures'
            })
            activities.append({
                'icon': 'check-circle',
                'title': 'Devoir soumis',
                'description': 'Devoir de Physique soumis avec succès',
                'time': 'Il y a 1 jour'
            })
        
        if user.is_teacher:
            activities.append({
                'icon': 'person-plus',
                'title': 'Nouvel étudiant',
                'description': 'Jean Dupont a rejoint votre cours',
                'time': 'Il y a 3 jours'
            })
            activities.append({
                'icon': 'star',
                'title': 'Évaluation',
                'description': 'Vous avez reçu une nouvelle évaluation',
                'time': 'Il y a 5 jours'
            })
        
        activities.append({
            'icon': 'bell',
            'title': 'Notification',
            'description': 'Votre profil a été mis à jour',
            'time': 'Il y a 1 semaine'
        })
        
        return activities


class SettingsView(LoginRequiredMixin, TemplateView):
    """User settings and preferences"""
    template_name = 'utilisateur/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['notification_preferences'] = {
            'email_notifications': True,
            'course_updates': True,
            'assignment_reminders': True,
            'new_messages': True,
        }
        
        context['privacy_settings'] = {
            'profile_visibility': 'public',
            'show_email': False,
            'show_phone': False,
            'activity_feed': True,
        }
        
        return context


class NotificationView(LoginRequiredMixin, TemplateView):
    """User notifications view"""
    template_name = 'utilisateur/notifications.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        notifications = [
            {
                'id': 1,
                'title': 'Rappel de cours',
                'message': 'Votre cours de Mathématiques commence dans 30 minutes',
                'type': 'reminder',
                'time': 'Il y a 10 minutes',
                'read': False,
                'icon': 'bell'
            },
            {
                'id': 2,
                'title': 'Nouveau message',
                'message': 'Vous avez reçu un message de votre enseignant',
                'type': 'message',
                'time': 'Il y a 2 heures',
                'read': True,
                'icon': 'chat'
            },
            {
                'id': 3,
                'title': 'Devoir corrigé',
                'message': 'Votre devoir de Physique a été noté',
                'type': 'grade',
                'time': 'Il y a 1 jour',
                'read': True,
                'icon': 'file-earmark-text'
            },
        ]
        
        context['notifications'] = notifications
        context['unread_count'] = sum(1 for n in notifications if not n['read'])
        
        return context
    

@login_required
def get_user_stats(request):
    """Get user statistics for dashboard widgets"""
    user = request.user
    stats = {}
    
    if user.is_student and hasattr(user, 'student_profile'):
        enrollments = user.student_profile.enrollments.filter(is_active=True)
        stats.update({
            'total_courses': enrollments.count(),
            'completed_courses': enrollments.filter(status='completed').count(),
            'active_courses': enrollments.filter(status='active').count(),
            'avg_grade': 85,  # This would be calculated from actual grades
        })
    
    if user.is_teacher and hasattr(user, 'teacher_profile'):
        teacher_enrollments = user.teacher_profile.enrollments.filter(is_active=True)
        stats.update({
            'total_students': teacher_enrollments.count(),
            'active_students': teacher_enrollments.filter(is_active=True).count(),
            'avg_rating': 4.8,
        })
    
    return JsonResponse(stats)


class ProfileCompletionView(LoginRequiredMixin, TemplateView):
    """Guide users through profile completion"""
    template_name = 'utilisateur/profile_completion.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Calculate completion percentage
        completion_steps = []
        total_steps = 5
        completed_steps = 0
        
        # Step 1: Basic info
        if user.first_name and user.last_name and user.email:
            completed_steps += 1
            completion_steps.append({
                'name': 'Informations de base',
                'completed': True,
                'icon': 'check-circle-fill',
                'color': 'success'
            })
        else:
            completion_steps.append({
                'name': 'Informations de base',
                'completed': False,
                'icon': 'circle',
                'color': 'secondary'
            })
        
        # Step 2: Profile picture
        if user.profile_pic and user.profile_pic.name != 'profile_pics/default.png':
            completed_steps += 1
            completion_steps.append({
                'name': 'Photo de profil',
                'completed': True,
                'icon': 'check-circle-fill',
                'color': 'success'
            })
        else:
            completion_steps.append({
                'name': 'Photo de profil',
                'completed': False,
                'icon': 'circle',
                'color': 'secondary'
            })
        
        # Step 3: Student profile (if applicable)
        if user.is_student:
            if hasattr(user, 'student_profile') and user.student_profile.level:
                completed_steps += 1
                completion_steps.append({
                    'name': 'Profil étudiant',
                    'completed': True,
                    'icon': 'check-circle-fill',
                    'color': 'success'
                })
            else:
                completion_steps.append({
                    'name': 'Profil étudiant',
                    'completed': False,
                    'icon': 'circle',
                    'color': 'secondary'
                })

        # Step 5: Preferences
        completed_steps += 1  # Assume preferences are set
        completion_steps.append({
            'name': 'Préférences',
            'completed': True,
            'icon': 'check-circle-fill',
            'color': 'success'
        })
        
        completion_percentage = int((completed_steps / total_steps) * 100)
        
        context.update({
            'completion_steps': completion_steps,
            'completion_percentage': completion_percentage,
            'completed_steps': completed_steps,
            'total_steps': total_steps,
        })
        
        return context
    

@login_required
def get_profile_picture_urls(request):
    """Get URLs for all profile pictures of the user"""
    user = request.user
    urls = {}
    
    if hasattr(user, 'student_profile'):
        urls['student'] = user.student_profile.profile_pic.url if user.student_profile.profile_pic else None
    
    return JsonResponse(urls)


@login_required
def set_active_profile_picture_view(request):
    """Set which profile picture to display (for dual-role users)"""
    if request.method == 'POST':
        profile_type = request.POST.get('profile_type')
        
        if profile_type in ['student']:
            request.session['active_profile_pic'] = profile_type
            request.session.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Photo {profile_type} sélectionnée comme photo active'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Requête invalide'
    }, status=400)


@login_required
def get_profile_completion(request):
    """Calculate and return profile completion percentage"""
    user = request.user
    total_steps = 5
    completed_steps = 0
    
    # Step 1: Basic info
    if user.first_name and user.last_name and user.email:
        completed_steps += 1
    
    # Step 2: Profile picture
    if hasattr(user, 'student_profile') and user.student_profile.profile_pic and user.student_profile.profile_pic.name != 'profile_pics/default.png':
        completed_steps += 1
    elif hasattr(user, 'teacher_profile') and user.teacher_profile.profile_pic and user.teacher_profile.profile_pic.name != 'profile_pics/default.png':
        completed_steps += 1
    
    # Step 3: Student profile completion
    if user.is_student and hasattr(user, 'student_profile'):
        if user.student_profile.level and user.student_profile.institution:
            completed_steps += 1
    
    # Step 5: Phone number (optional bonus)
    if user.phone_number:
        completed_steps += 1
    
    completion_percentage = int((completed_steps / total_steps) * 100)
    
    return JsonResponse({
        'percentage': completion_percentage,
        'completed_steps': completed_steps,
        'total_steps': total_steps
    })


@login_required
@require_POST
def logout_other_sessions(request):
    """Logout all other sessions except current one"""
    try:
        current_session_key = request.session.session_key
        
        # Get all sessions for this user
        user_sessions = Session.objects.filter(
            expire_date__gte=timezone.now()
        )
        
        # Delete all sessions except current one
        deleted_count = 0
        for session in user_sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(request.user.id):
                if session.session_key != current_session_key:
                    session.delete()
                    deleted_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'{deleted_count} session(s) déconnectée(s)',
            'deleted_count': deleted_count
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Update the AJAX upload view
@login_required
@csrf_exempt
def ajax_upload_profile_picture(request):
    """Handle AJAX profile picture upload with cropping"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        user = request.user
        profile_picture = request.FILES['profile_picture']
        
        try:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if profile_picture.content_type not in allowed_types:
                return JsonResponse({
                    'success': False,
                    'error': 'Format d\'image non supporté. Utilisez JPG, PNG, GIF ou WebP.'
                })
            
            # Validate file size (max 5MB)
            if profile_picture.size > 5 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'error': 'L\'image est trop volumineuse (max 5MB).'
                })
            
            # Process image with PIL for optimization
            try:
                img = Image.open(profile_picture)
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize to optimal dimensions (400x400)
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                
                # Save to bytes
                img_io = io.BytesIO()
                img.save(img_io, format='JPEG', quality=85, optimize=True)
                img_content = ContentFile(img_io.getvalue())
                
                # Create filename
                timestamp = int(timezone.now().timestamp())
                filename = f"user_{user.id}_{timestamp}.jpg"
                
            except Exception as img_error:
                return JsonResponse({
                    'success': False,
                    'error': f'Erreur de traitement d\'image: {str(img_error)}'
                })
            
            # Delete old picture if exists and not default
            if user.profile_pic and user.profile_pic.name != 'profile_pics/default.png':
                try:
                    if os.path.isfile(user.profile_pic.path):
                        os.remove(user.profile_pic.path)
                except:
                    pass  # If file doesn't exist, continue
            
            # Save new picture to User model
            user.profile_pic.save(filename, img_content)
            user.save()
            
            # Get the URL of the saved image
            image_url = user.profile_pic.url
            
            return JsonResponse({
                'success': True,
                'message': 'Photo de profil mise à jour avec succès !',
                'image_url': image_url
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Erreur lors du téléchargement : {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Aucune image fournie.'
    })


@login_required
def delete_profile_picture(request):
    """Supprimer la photo de profil de l'utilisateur"""
    user = request.user
    
    if request.method == 'POST':
        try:
            if user.profile_pic and user.profile_pic.name != 'profile_pics/default.png':
                # Supprimer le fichier physique
                if os.path.isfile(user.profile_pic.path):
                    os.remove(user.profile_pic.path)
                
                # Réinitialiser à la photo par défaut
                user.profile_pic = 'profile_pics/default.png'
                user.save()
                
                messages.success(request, "✅ Photo de profil supprimée.")
            else:
                messages.info(request, "Vous utilisez déjà la photo par défaut.")
        
        except Exception as e:
            messages.error(request, f"Erreur lors de la suppression : {str(e)}")
    
    # Rediriger vers l'onglet approprié
    redirect_tab = request.POST.get('redirect_tab', 'general')
    return redirect(f'{reverse("utilisateur:profile_update")}?tab={redirect_tab}')


def get_recent_activities(user):
    """Generate recent activity data for profile page"""
    activities = []
    
    # Add recent enrollments for students
    if user.is_student and hasattr(user, 'student_profile'):
        recent_enrollments = user.student_profile.enrollments.order_by('-enrollment_date')[:3]
        for enrollment in recent_enrollments:
            activities.append({
                'description': f"A rejoint le cours {enrollment.subject.name}",
                'time': f"Il y a {(timezone.now() - enrollment.enrollment_date).days} jours"
            })
    
    # Add account activities
    activities.append({
        'description': "Dernière connexion",
        'time': f"Il y a {(timezone.now() - user.last_login).days} jours" if user.last_login else "Jamais"
    })
    
    # Add profile update if recent
    if user.date_joined:
        days_since_joined = (timezone.now() - user.date_joined).days
        if days_since_joined < 7:
            activities.append({
                'description': "A rejoint la plateforme",
                'time': f"Il y a {days_since_joined} jours"
            })
    
    return activities[:5]  # Return only 5 most recent activiti


# Helper function to calculate profile completion
def calculate_profile_completion(user):
    """Calculate profile completion percentage"""
    total_fields = 0
    filled_fields = 0
    
    # User model fields
    user_fields = ['first_name', 'last_name', 'email', 'phone_number', 'gender', 'bio', 'profile_pic']
    for field in user_fields:
        total_fields += 1
        value = getattr(user, field)
        if value and (field != 'profile_pic' or value != 'profile_pics/default.png'):
            filled_fields += 1
    
    # Check role-specific profile
    if user.is_student and hasattr(user, 'student_profile'):
        student = user.student_profile
        student_fields = ['level', 'institution', 'student_id_number']
        for field in student_fields:
            total_fields += 1
            if getattr(student, field):
                filled_fields += 1
    
    if total_fields == 0:
        return 0
    
    return int((filled_fields / total_fields) * 100)


@login_required
def profile_view(request):
    """Main profile view that adapts to user role"""
    user = request.user
    context = {
        'user': user,
        'profile_completion': calculate_profile_completion(user),
        'active_tab': 'general'
    }
    
    # Add role-specific data
    if user.is_student and hasattr(user, 'student_profile'):
        student_profile = user.student_profile
        context['student_profile'] = student_profile
        
        # Student-specific stats with subscriptions
        active_subscriptions = Subscription.objects.filter(
            student=student_profile,
            payement_status='approved'
        ).filter(
            Q(start_date__lte=datetime.now().date()) &
            Q(expires_at__gte=datetime.now().date())
        )
        
        context['subscription_count'] = active_subscriptions.count()
        context['active_subscription'] = active_subscriptions.first()
        
        # Get subscription features if exists
        if context['active_subscription']:
            subscription = context['active_subscription']
            context['subscription_features'] = subscription.feature.get_feature_list() if subscription.feature else []
            context['days_remaining'] = subscription.calculate_days_available()
            
            # Quiz limits from subscription
            context['remaining_mcq'] = subscription.get_remaining_mcq()
            context['remaining_qa'] = subscription.get_remaining_qa()
            context['remaining_tf'] = subscription.get_remaining_tf()
            context['remaining_mcq_exams'] = subscription.get_remaining_mcq_exams()
            context['remaining_qa_exams'] = subscription.get_remaining_qa_exams()
        
        # Calculate average grade from quiz results
        try:
            quiz_results = MCQResult.objects.filter(student=student_profile)
            if quiz_results.exists():
                context['average_grade'] = quiz_results.aggregate(Avg('score'))['score__avg']
        except:
            context['average_grade'] = 0
        
        # Recent study sessions
        try:
            context['recent_sessions'] = StudySession.objects.filter(
                student=student_profile
            ).order_by('-start_time')[:5]
        except:
            context['recent_sessions'] = []
    

    # Recent activities - simplified for now
    context['recent_activities'] = [
        {'description': 'Connexion réussie', 'time': 'Aujourd\'hui, 10:30'},
        {'description': 'Profil mis à jour', 'time': 'Hier, 14:45'},
        {'description': 'Quiz complété', 'time': '2 jours'},
    ]
    
    return render(request, 'utilisateur/profile.html', context)


@login_required
def role_profile_update(request, role):
    """Update role-specific profile information"""
    user = request.user
    
    if role == 'student' and user.is_student:
        # Check if student profile exists, if not create it
        student_profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={
                'is_active_student': True
            }
        )
        
        if request.method == 'POST':
            from .forms import StudentProfileUpdateForm
            form = StudentProfileUpdateForm(request.POST, instance=student_profile)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profil étudiant mis à jour avec succès!')
                return redirect('utilisateur:profile')
        else:
            from .forms import StudentProfileUpdateForm
            form = StudentProfileUpdateForm(instance=student_profile)
        
        return render(request, 'utilisateur/role_profile_update.html', {
            'form': form,
            'role': 'student',
            'user': user,
            'profile': student_profile,
            'title': 'Modifier le profil étudiant'
        })
    
    messages.error(request, 'Action non autorisée.')
    return redirect('utilisateur:profile')


@login_required
def update_profile_pic(request):
    """AJAX endpoint to update profile picture"""
    if request.method == 'POST' and request.FILES.get('profile_pic'):
        user = request.user
        user.profile_pic = request.FILES['profile_pic']
        user.save()
        
        return JsonResponse({
            'success': True,
            'url': user.profile_pic.url,
            'message': 'Photo de profil mise à jour avec succès!'
        })
    
    return JsonResponse({'success': False, 'error': 'Requête invalide'})


@login_required
def delete_profile_pic(request):
    """Delete user's profile picture"""
    if request.method == 'POST':
        user = request.user
        if user.profile_pic and user.profile_pic.name != 'profile_pics/default.png':
            # Delete the file
            user.profile_pic.delete(save=False)
        
        user.profile_pic = 'profile_pics/default.png'
        user.save()
        
        messages.success(request, 'Photo de profil supprimée avec succès.')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'url': user.profile_pic.url,
                'message': 'Photo de profil supprimée avec succès.'
            })
    
    return redirect('utilisateur:profile_update')


@login_required
def profile_stats(request):
    """Get profile statistics for dashboard"""
    user = request.user
    stats = {
        'profile_completion': calculate_profile_completion(user),
        'subscription_count': 0,
        'average_grade': 0,
    }
    
    if user.is_student and hasattr(user, 'student_profile'):
        student = user.student_profile
        
        # Subscription stats
        active_subscriptions = Subscription.objects.filter(
            student=student,
            payement_status='approved'
        ).filter(
            Q(start_date__lte=datetime.now().date()) &
            Q(expires_at__gte=datetime.now().date())
        )
        
        stats['subscription_count'] = active_subscriptions.count()
        
        # Average grade
        try:
            quiz_results = MCQResult.objects.filter(student=student)
            if quiz_results.exists():
                stats['average_grade'] = quiz_results.aggregate(Avg('score'))['score__avg']
        except:
            pass
    
    return JsonResponse(stats)


class ProfileView(View):
    """Class-based view for profile management"""
    
    @method_decorator(login_required)
    def get(self, request, *args, **kwargs):
        return profile_view(request)
    
    @method_decorator(login_required)
    def post(self, request, *args, **kwargs):
        return self.update_profile(request)
    
    def update_profile(self, request):
        """Handle profile updates"""
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès!')
            return redirect('utilisateur:profile')
        
        return render(request, 'utilisateur/profile_update.html', {'form': form})


# Update the profile_update function
@login_required
def profile_update(request):
    """Update user profile information with independent role forms"""
    user = request.user
    next_url = request.GET.get('next', 'utilisateur:profile')
    active_tab = request.GET.get('tab', 'general')
    
    if request.method == 'POST':
        if 'save_general' in request.POST:
            form = UserProfileForm(request.POST, request.FILES, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profil général mis à jour avec succès!')
                return redirect('utilisateur:profile')
        elif 'save_student' in request.POST and user.is_student:
            student_profile = getattr(user, 'student_profile', None)
            if student_profile:
                student_form = StudentProfileUpdateForm(request.POST, instance=student_profile)
                if student_form.is_valid():
                    student_form.save()
                    messages.success(request, 'Profil étudiant mis à jour avec succès!')
                    return redirect('utilisateur:profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
        'user': user,
        'active_tab': active_tab,
        'next_url': next_url,
    }
    
    # Add role-specific forms
    if user.is_student:
        student_profile, created = StudentProfile.objects.get_or_create(
            user=user,
            defaults={'is_active_student': True}
        )
        context['student_form'] = StudentProfileUpdateForm(instance=student_profile)

    return render(request, 'utilisateur/profile_update.html', context)


@login_required
def list_membres(request):
    users = User.objects.all()
    profiles = User.objects.all()
    
    # Compter les niveaux distincts
    level_count = StudentProfile.objects.exclude(
        level__isnull=True
    ).exclude(
        level=''
    ).values('level').distinct().count()
    
    return render(request, "utilisateur/liste_membres.html", {
        'users': users, 
        'profiles': profiles,
        'level_count': level_count
    })


@login_required
def voir_profil(request, user_id):
    person = User.objects.get(id=user_id) 
    return render (request, "utilisateur/voir_profil.html", {"person": person})


