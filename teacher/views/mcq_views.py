from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from lecon.models import Unite, Chapter
from quizzes.models import MCQ, MCQResult
from ..decorators import teacher_required, teacher_of_unite_required, teacher_owns_chapter_required
from ..forms import MCQForm


@login_required
@teacher_required
def mcq_list(request, unite_id=None, chapter_id=None):
    """
    Liste des QCM
    Peut être filtrée par unité ou par chapitre
    """
    teacher = request.user
    
    # Récupérer les unités enseignées
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    # Base queryset: QCM créés par l'enseignant dans ses unités
    mcqs = MCQ.objects.filter(
        # created_by=teacher,
        chapter__ue__in=teaching_unites
    ).select_related('chapter', 'chapter__ue')
    
    unite = None
    chapitre = None
    
    if chapter_id:
        chapitre = get_object_or_404(Chapter, pk=chapter_id)
        if chapitre.ue not in teaching_unites:
            messages.error(request, 'Accès non autorisé à ce chapitre.')
            return redirect('teacher:mcq_list')
        mcqs = mcqs.filter(chapter=chapitre)
        unite = chapitre.ue
    elif unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite not in teaching_unites:
            messages.error(request, 'Accès non autorisé à cette unité.')
            return redirect('teacher:mcq_list')
        mcqs = mcqs.filter(chapter__ue=unite)
    
    # Filtrage
    search_query = request.GET.get('q')
    if search_query:
        mcqs = mcqs.filter(Q(question__icontains=search_query))
    
    # Pagination
    paginator = Paginator(mcqs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CORRECTION: Pour calculer la moyenne des scores des QCM,
    # on filtre MCQResult par les chapitres des QCM sélectionnés
    # Récupérer les IDs des chapitres des QCM
    chapters_ids = mcqs.values_list('chapter_id', flat=True).distinct()
    
    avg_score = MCQResult.objects.filter(
        chapter_id__in=chapters_ids
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'mcqs': page_obj,
        'unite': unite,
        'chapitre': chapitre,
        'teaching_unites': teaching_unites,
        'search_query': search_query,
        'total_mcqs': mcqs.count(),
        'avg_score': round(avg_score, 1),
    }
    
    return render(request, 'teacher/quizzes/mcq/liste.html', context)


@login_required
@teacher_required
def mcq_create(request, chapter_id):
    """
    Créer un QCM pour un chapitre
    """
    chapitre = get_object_or_404(Chapter, pk=chapter_id)
    unite = chapitre.ue
    
    # Vérifier que l'enseignant a accès à l'unité
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à ce chapitre.')
        return redirect('teacher:mcq_list')
    
    if request.method == 'POST':
        form = MCQForm(request.POST)
        if form.is_valid():
            mcq = form.save(commit=False)
            mcq.chapter = chapitre
            mcq.created_by = request.user
            mcq.save()
            messages.success(request, 'QCM créé avec succès.')
            return redirect('teacher:mcq_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = MCQForm()
    
    context = {
        'form': form,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Créer un QCM - {chapitre.title}',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/quizzes/mcq/formulaire.html', context)


@login_required
@teacher_required
def mcq_edit(request, pk):
    """
    Modifier un QCM
    """
    mcq = get_object_or_404(MCQ, pk=pk)
    chapitre = mcq.chapter
    unite = chapitre.ue
    
    # Vérifier que l'enseignant a accès
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à ce QCM.')
        return redirect('teacher:mcq_list')
    
    if request.method == 'POST':
        form = MCQForm(request.POST, instance=mcq)
        if form.is_valid():
            form.save()
            messages.success(request, 'QCM modifié avec succès.')
            return redirect('teacher:mcq_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = MCQForm(instance=mcq)
    
    context = {
        'form': form,
        'mcq': mcq,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Modifier QCM - {mcq.question[:50]}...',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/quizzes/mcq/formulaire.html', context)


@login_required
@teacher_required
def mcq_delete(request, pk):
    """
    Supprimer un QCM
    """
    mcq = get_object_or_404(MCQ, pk=pk)
    chapitre = mcq.chapter
    unite = chapitre.ue
    
    # Vérifier que l'enseignant a accès
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à ce QCM.')
        return redirect('teacher:mcq_list')
    
    if request.method == 'POST':
        mcq_question = mcq.question[:50]
        mcq.delete()
        messages.success(request, f'QCM "{mcq_question}..." supprimé avec succès.')
        return redirect('teacher:mcq_list_by_unite', unite_id=unite.id)
    
    context = {
        'mcq': mcq,
        'chapitre': chapitre,
        'unite': unite,
        'title': 'Supprimer le QCM',
    }
    
    return render(request, 'teacher/quizzes/mcq/supprimer.html', context)

