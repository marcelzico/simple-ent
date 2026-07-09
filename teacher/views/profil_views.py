from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from ..decorators import teacher_required
from ..forms import TeacherProfileForm, NotificationPreferenceForm
from ..models import NotificationPreference
from teacher.models import TeacherProfile
from lecon.models import Unite


@login_required
@teacher_required
def profil_index(request):
    """
    Page de profil de l'enseignant
    """
    teacher = request.user
    
    # Récupérer ou créer le profil enseignant
    try:
        profile = teacher.teacher_profile
    except TeacherProfile.DoesNotExist:
        profile = TeacherProfile.objects.create(user=teacher)
    
    # Récupérer les unités enseignées
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    context = {
        'teacher': teacher,
        'profile': profile,
        'teaching_unites': teaching_unites,
        'teaching_unites_count': teaching_unites.count(),
    }
    
    return render(request, 'teacher/profil/index.html', context)


@login_required
@teacher_required
def profil_modifier(request):
    """
    Modifier le profil de l'enseignant
    """
    teacher = request.user
    
    try:
        profile = teacher.teacher_profile
    except TeacherProfile.DoesNotExist:
        profile = TeacherProfile.objects.create(user=teacher)
    
    if request.method == 'POST':
        form = TeacherProfileForm(request.POST, request.FILES, instance=profile, user=teacher)
        if form.is_valid():
            form.save(user=teacher)
            messages.success(request, 'Votre profil a été mis à jour avec succès.')
            return redirect('teacher:profil_index')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = TeacherProfileForm(instance=profile, user=teacher)
    
    context = {
        'form': form,
        'profile': profile,
        'title': 'Modifier mon profil',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/profil/formulaire.html', context)


@login_required
@teacher_required
def profil_changer_mot_de_passe(request):
    """
    Changer le mot de passe de l'enseignant
    """
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Votre mot de passe a été modifié avec succès.')
            return redirect('teacher:profil_index')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'title': 'Changer mon mot de passe',
        'button_text': 'Changer',
    }
    
    return render(request, 'teacher/profil/changer_mdp.html', context)


@login_required
@teacher_required
def profil_notifications(request):
    """
    Gérer les préférences de notifications
    """
    teacher = request.user
    
    # Récupérer ou créer les préférences
    notification_prefs = []
    for notif_type, label in NotificationPreference.NOTIFICATION_TYPES:
        pref, created = NotificationPreference.objects.get_or_create(
            teacher=teacher,
            notification_type=notif_type,
            defaults={
                'is_enabled': True,
                'send_email': True,
                'send_sms': False,
            }
        )
        notification_prefs.append(pref)
    
    # Traitement du formulaire
    if request.method == 'POST':
        for pref in notification_prefs:
            is_enabled = request.POST.get(f'is_enabled_{pref.notification_type}') == 'on'
            send_email = request.POST.get(f'send_email_{pref.notification_type}') == 'on'
            send_sms = request.POST.get(f'send_sms_{pref.notification_type}') == 'on'
            
            pref.is_enabled = is_enabled
            pref.send_email = send_email
            pref.send_sms = send_sms
            pref.save()
        
        messages.success(request, 'Vos préférences de notification ont été sauvegardées.')
        return redirect('teacher:profil_notifications')
    
    context = {
        'notification_prefs': notification_prefs,
    }
    
    return render(request, 'teacher/profil/notifications.html', context)


@login_required
@teacher_required
def profil_notification_update(request, notif_type):
    """
    Mise à jour AJAX d'une notification
    """
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    teacher = request.user
    is_enabled = request.POST.get('is_enabled') == 'true'
    
    try:
        pref = NotificationPreference.objects.get(
            teacher=teacher,
            notification_type=notif_type
        )
        pref.is_enabled = is_enabled
        pref.save()
        return JsonResponse({'success': True})
    except NotificationPreference.DoesNotExist:
        return JsonResponse({'error': 'Préférence non trouvée'}, status=404)
    