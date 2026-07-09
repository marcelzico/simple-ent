from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from lecon.models import Unite
from clinical_case_simple.models import Enoncé, QCM, QestionRéponse, VraiFaux, Illustraion, ExamAttempt
from ..decorators import teacher_required, teacher_of_unite_required
from ..forms import (
    EnonceForm, ClinicalCaseQCMForm, ClinicalCaseQRForm, ClinicalCaseVFForm
)
from django.db import models


# ==================== GESTION DESeÉNONCÉS ====================

@login_required
@teacher_required
def cas_liste(request, unite_id=None):
    """
    Liste des cas cliniques eénoncés)
    """
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    cas = Enoncé.objects.filter(
        auteur=teacher
    ).select_related('unite_associee')
    
    unite = None
    if unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite in teaching_unites:
            cas = cas.filter(unite_associee=unite)
    
    # Filtrage
    search_query = request.GET.get('q')
    if search_query:
        cas = cas.filter(
            Q(anonce_du_sujet__icontains=search_query) |
            Q(specialté__icontains=search_query)
        )
    
    publie_filter = request.GET.get('publie')
    if publie_filter == 'oui':
        cas = cas.filter(publié=True)
    elif publie_filter == 'non':
        cas = cas.filter(publié=False)
    
    paginator = Paginator(cas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'cas_liste': page_obj,
        'unite': unite,
        'teaching_unites': teaching_unites,
        'search_query': search_query,
        'publie_filter': publie_filter,
        'total_cas': cas.count(),
    }
    
    return render(request, 'teacher/cas_cliniques/liste.html', context)


@login_required
@teacher_required
def cas_creer(request, unite_id=None):
    """
    Créer un nouveau cas clinique
    """
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    if request.method == 'POST':
        form = EnonceForm(request.POST)
        if form.is_valid():
            cas = form.save(commit=False)
            cas.auteur = teacher
            if unite_id:
                cas.unite_associee = get_object_or_404(Unite, pk=unite_id)
            cas.save()
            messages.success(request, 'Cas clinique créé avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = EnonceForm()
        if unite_id:
            unite = get_object_or_404(Unite, pk=unite_id)
            form.fields['niveau_cible'].initial = unite.level
    
    context = {
        'form': form,
        'teaching_unites': teaching_unites,
        'unite_id': unite_id,
        'title': 'Créer un cas clinique',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/cas_cliniques/formulaire.html', context)


@login_required
@teacher_required
def cas_modifier(request, pk):
    """
    Modifier un cas clinique
    """
    cas = get_object_or_404(Enoncé, pk=pk)
    
    # Vérifier que l'enseignant est l'auteur
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Vous n\'êtes pas autorisé à modifier ce cas clinique.')
        return redirect('teacher:cas_liste')
    
    if request.method == 'POST':
        form = EnonceForm(request.POST, instance=cas)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cas clinique modifié avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = EnonceForm(instance=cas)
    
    context = {
        'form': form,
        'cas': cas,
        'title': f'Modifier - {cas.id}',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/cas_cliniques/formulaire.html', context)


@login_required
@teacher_required
def cas_supprimer(request, pk):
    """
    Supprimer un cas clinique
    """
    cas = get_object_or_404(Enoncé, pk=pk)
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Vous n\'êtes pas autorisé à supprimer ce cas.')
        return redirect('teacher:cas_liste')
    
    if request.method == 'POST':
        cas_id = cas.id
        cas.delete()
        messages.success(request, f'Cas clinique #{cas_id} supprimé avec succès.')
        return redirect('teacher:cas_liste')
    
    context = {
        'cas': cas,
        'title': 'Supprimer le cas clinique',
    }
    
    return render(request, 'teacher/cas_cliniques/supprimer.html', context)


@login_required
@teacher_required
def cas_detail(request, pk):
    """
    Détail d'un cas clinique avec toutes ses questions
    """
    cas = get_object_or_404(Enoncé, pk=pk)
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_liste')
    
    # Récupérer toutes les questions associées
    qcms = QCM.objects.filter(enoncé=cas)
    qrs = QestionRéponse.objects.filter(enoncé=cas)
    vfs = VraiFaux.objects.filter(enoncé=cas)
    illustrations = Illustraion.objects.filter(enoncé=cas)
    
    # Statistiques des tentatives
    attempts = ExamAttempt.objects.filter(enonce=cas)
    attempts_count = attempts.count()
    completed_attempts = attempts.filter(is_completed=True)
    avg_score = completed_attempts.aggregate(avg=models.Avg('score_percentage'))['avg'] or 0
    
    context = {
        'cas': cas,
        'qcms': qcms,
        'qrs': qrs,
        'vfs': vfs,
        'illustrations': illustrations,
        'attempts_count': attempts_count,
        'completed_attempts_count': completed_attempts.count(),
        'avg_score': round(avg_score, 1),
    }
    
    return render(request, 'teacher/cas_cliniques/detail.html', context)


# ==================== GESTION DES QCM POUR CAS ====================

@login_required
@teacher_required
def cas_qcm_creer(request, cas_pk):
    """
    Ajouter un QCM à un cas clinique
    """
    cas = get_object_or_404(Enoncé, pk=cas_pk)
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseQCMForm(request.POST)
        if form.is_valid():
            qcm = form.save(commit=False)
            qcm.enoncé = cas
            qcm.save()
            messages.success(request, 'QCM ajouté avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseQCMForm()
    
    context = {
        'form': form,
        'cas': cas,
        'title': 'Ajouter un QCM',
        'button_text': 'Ajouter',
        'type': 'qcm',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_qcm_modifier(request, pk):
    """
    Modifier un QCM d'un cas clinique
    """
    qcm = get_object_or_404(QCM, pk=pk)
    cas = qcm.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseQCMForm(request.POST, instance=qcm)
        if form.is_valid():
            form.save()
            messages.success(request, 'QCM modifié avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseQCMForm(instance=qcm)
    
    context = {
        'form': form,
        'qcm': qcm,
        'cas': cas,
        'title': 'Modifier le QCM',
        'button_text': 'Enregistrer',
        'type': 'qcm',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_qcm_supprimer(request, pk):
    """
    Supprimer un QCM d'un cas clinique
    """
    qcm = get_object_or_404(QCM, pk=pk)
    cas = qcm.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        qcm.delete()
        messages.success(request, 'QCM supprimé avec succès.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    context = {
        'qcm': qcm,
        'cas': cas,
        'title': 'Supprimer le QCM',
    }
    
    return render(request, 'teacher/cas_cliniques/question_supprimer.html', context)


# ==================== GESTION DES QUESTIONS/RÉPONSES POUR CAS ====================

@login_required
@teacher_required
def cas_qr_creer(request, cas_pk):
    """
    Ajouter une question/réponse à un cas clinique
    """
    cas = get_object_or_404(Enoncé, pk=cas_pk)
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseQRForm(request.POST)
        if form.is_valid():
            qr = form.save(commit=False)
            qr.enoncé = cas
            qr.save()
            messages.success(request, 'Question/Réponse ajoutée avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseQRForm()
    
    context = {
        'form': form,
        'cas': cas,
        'title': 'Ajouter une question/réponse',
        'button_text': 'Ajouter',
        'type': 'qr',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_qr_modifier(request, pk):
    """
    Modifier une question/réponse d'un cas clinique
    """
    qr = get_object_or_404(QestionRéponse, pk=pk)
    cas = qr.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseQRForm(request.POST, instance=qr)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question/Réponse modifiée avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseQRForm(instance=qr)
    
    context = {
        'form': form,
        'qr': qr,
        'cas': cas,
        'title': 'Modifier la question/réponse',
        'button_text': 'Enregistrer',
        'type': 'qr',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_qr_supprimer(request, pk):
    """
    Supprimer une question/réponse d'un cas clinique
    """
    qr = get_object_or_404(QestionRéponse, pk=pk)
    cas = qr.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        qr.delete()
        messages.success(request, 'Question/Réponse supprimée avec succès.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    context = {
        'qr': qr,
        'cas': cas,
        'title': 'Supprimer la question/réponse',
    }
    
    return render(request, 'teacher/cas_cliniques/question_supprimer.html', context)


# ==================== GESTION DES VRAI/FAUX POUR CAS ====================

@login_required
@teacher_required
def cas_vf_creer(request, cas_pk):
    """
    Ajouter une question Vrai/Faux à un cas clinique
    """
    cas = get_object_or_404(Enoncé, pk=cas_pk)
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseVFForm(request.POST)
        if form.is_valid():
            vf = form.save(commit=False)
            vf.enoncé = cas
            vf.save()
            messages.success(request, 'Question Vrai/Faux ajoutée avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseVFForm()
    
    context = {
        'form': form,
        'cas': cas,
        'title': 'Ajouter une question Vrai/Faux',
        'button_text': 'Ajouter',
        'type': 'vf',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_vf_modifier(request, pk):
    """
    Modifier une question Vrai/Faux d'un cas clinique
    """
    vf = get_object_or_404(VraiFaux, pk=pk)
    cas = vf.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        form = ClinicalCaseVFForm(request.POST, instance=vf)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question Vrai/Faux modifiée avec succès.')
            return redirect('teacher:cas_detail', pk=cas.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = ClinicalCaseVFForm(instance=vf)
    
    context = {
        'form': form,
        'vf': vf,
        'cas': cas,
        'title': 'Modifier la question Vrai/Faux',
        'button_text': 'Enregistrer',
        'type': 'vf',
    }
    
    return render(request, 'teacher/cas_cliniques/question_form.html', context)


@login_required
@teacher_required
def cas_vf_supprimer(request, pk):
    """
    Supprimer une question Vrai/Faux d'un cas clinique
    """
    vf = get_object_or_404(VraiFaux, pk=pk)
    cas = vf.enoncé
    
    if cas.auteur != request.user and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    if request.method == 'POST':
        vf.delete()
        messages.success(request, 'Question Vrai/Faux supprimée avec succès.')
        return redirect('teacher:cas_detail', pk=cas.id)
    
    context = {
        'vf': vf,
        'cas': cas,
        'title': 'Supprimer la question Vrai/Faux',
    }
    
    return render(request, 'teacher/cas_cliniques/question_supprimer.html', context)


