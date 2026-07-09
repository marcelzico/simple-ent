from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from lecon.models import Unite, Chapter
from quizzes.models import QuestionAnswer, QAResult
from ..decorators import teacher_required
from ..forms import QuestionAnswerForm


@login_required
@teacher_required
def qa_list(request, unite_id=None, chapter_id=None):
    """
    Liste des questions/réponses
    """
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    qas = QuestionAnswer.objects.filter(
        # created_by=teacher,
        chapter__ue__in=teaching_unites
    ).select_related('chapter', 'chapter__ue')
    
    unite = None
    chapitre = None
    
    if chapter_id:
        chapitre = get_object_or_404(Chapter, pk=chapter_id)
        if chapitre.ue not in teaching_unites:
            messages.error(request, 'Accès non autorisé.')
            return redirect('teacher:qa_list')
        qas = qas.filter(chapter=chapitre)
        unite = chapitre.ue
    elif unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite not in teaching_unites:
            messages.error(request, 'Accès non autorisé.')
            return redirect('teacher:qa_list')
        qas = qas.filter(chapter__ue=unite)
    
    search_query = request.GET.get('q')
    if search_query:
        qas = qas.filter(Q(question__icontains=search_query))
    
    paginator = Paginator(qas, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CORRECTION: Filtrer par chapitres des QA
    chapters_ids = qas.values_list('chapter_id', flat=True).distinct()
    
    avg_score = QAResult.objects.filter(
        chapter_id__in=chapters_ids
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'qas': page_obj,
        'unite': unite,
        'chapitre': chapitre,
        'teaching_unites': teaching_unites,
        'search_query': search_query,
        'total_qas': qas.count(),
        'avg_score': round(avg_score, 1),
    }
    
    return render(request, 'teacher/quizzes/qa/liste.html', context)


@login_required
@teacher_required
def qa_create(request, chapter_id):
    """Créer une question/réponse"""
    chapitre = get_object_or_404(Chapter, pk=chapter_id)
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_list')
    
    if request.method == 'POST':
        form = QuestionAnswerForm(request.POST)
        if form.is_valid():
            qa = form.save(commit=False)
            qa.chapter = chapitre
            qa.created_by = request.user
            qa.save()
            messages.success(request, 'Question/Réponse créée avec succès.')
            return redirect('teacher:qa_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = QuestionAnswerForm()
    
    context = {
        'form': form,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Créer une question - {chapitre.title}',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/quizzes/qa/formulaire.html', context)


@login_required
@teacher_required
def qa_edit(request, pk):
    """Modifier une question/réponse"""
    qa = get_object_or_404(QuestionAnswer, pk=pk)
    chapitre = qa.chapter
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_list')
    
    if request.method == 'POST':
        form = QuestionAnswerForm(request.POST, instance=qa)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question/Réponse modifiée avec succès.')
            return redirect('teacher:qa_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = QuestionAnswerForm(instance=qa)
    
    context = {
        'form': form,
        'qa': qa,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Modifier - {qa.question[:50]}...',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/quizzes/qa/formulaire.html', context)


@login_required
@teacher_required
def qa_delete(request, pk):
    """Supprimer une question/réponse"""
    qa = get_object_or_404(QuestionAnswer, pk=pk)
    chapitre = qa.chapter
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_list')
    
    if request.method == 'POST':
        qa_question = qa.question[:50]
        qa.delete()
        messages.success(request, f'Question "{qa_question}..." supprimée.')
        return redirect('teacher:qa_list_by_unite', unite_id=unite.id)
    
    context = {
        'qa': qa,
        'chapitre': chapitre,
        'unite': unite,
        'title': 'Supprimer la question',
    }
    
    return render(request, 'teacher/quizzes/qa/supprimer.html', context)

