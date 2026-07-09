from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg
from lecon.models import Unite, Chapter
from quizzes.models import TrueFalseQuiz, TrueFalseResult
from ..decorators import teacher_required
from ..forms import TrueFalseForm


@login_required
@teacher_required
def tf_list(request, unite_id=None, chapter_id=None):
    """Liste des questions Vrai/Faux"""
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    tfs = TrueFalseQuiz.objects.filter(
        # created_by=teacher,
        chapter__ue__in=teaching_unites
    ).select_related('chapter', 'chapter__ue')
    
    unite = None
    chapitre = None
    
    if chapter_id:
        chapitre = get_object_or_404(Chapter, pk=chapter_id)
        if chapitre.ue not in teaching_unites:
            messages.error(request, 'Accès non autorisé.')
            return redirect('teacher:tf_list')
        tfs = tfs.filter(chapter=chapitre)
        unite = chapitre.ue
    elif unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite not in teaching_unites:
            messages.error(request, 'Accès non autorisé.')
            return redirect('teacher:tf_list')
        tfs = tfs.filter(chapter__ue=unite)
    
    search_query = request.GET.get('q')
    if search_query:
        tfs = tfs.filter(Q(question__icontains=search_query))
    
    paginator = Paginator(tfs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # CORRECTION: Filtrer par chapitres des TF
    chapters_ids = tfs.values_list('chapter_id', flat=True).distinct()
    
    avg_score = TrueFalseResult.objects.filter(
        chapter_id__in=chapters_ids
    ).aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'tfs': page_obj,
        'unite': unite,
        'chapitre': chapitre,
        'teaching_unites': teaching_unites,
        'search_query': search_query,
        'total_tfs': tfs.count(),
        'avg_score': round(avg_score, 1),
    }
    
    return render(request, 'teacher/quizzes/tf/liste.html', context)


@login_required
@teacher_required
def tf_create(request, chapter_id):
    """Créer une question Vrai/Faux"""
    chapitre = get_object_or_404(Chapter, pk=chapter_id)
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:tf_list')
    
    if request.method == 'POST':
        form = TrueFalseForm(request.POST)
        if form.is_valid():
            tf = form.save(commit=False)
            tf.chapter = chapitre
            tf.created_by = request.user
            tf.save()
            messages.success(request, 'Question Vrai/Faux créée avec succès.')
            return redirect('teacher:tf_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = TrueFalseForm()
    
    context = {
        'form': form,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Créer Vrai/Faux - {chapitre.title}',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/quizzes/tf/formulaire.html', context)


@login_required
@teacher_required
def tf_edit(request, pk):
    """Modifier une question Vrai/Faux"""
    tf = get_object_or_404(TrueFalseQuiz, pk=pk)
    chapitre = tf.chapter
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:tf_list')
    
    if request.method == 'POST':
        form = TrueFalseForm(request.POST, instance=tf)
        if form.is_valid():
            form.save()
            messages.success(request, 'Question Vrai/Faux modifiée avec succès.')
            return redirect('teacher:tf_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = TrueFalseForm(instance=tf)
    
    context = {
        'form': form,
        'tf': tf,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Modifier - {tf.question[:50]}...',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/quizzes/tf/formulaire.html', context)


@login_required
@teacher_required
def tf_delete(request, pk):
    """Supprimer une question Vrai/Faux"""
    tf = get_object_or_404(TrueFalseQuiz, pk=pk)
    chapitre = tf.chapter
    unite = chapitre.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:tf_list')
    
    if request.method == 'POST':
        tf_question = tf.question[:50]
        tf.delete()
        messages.success(request, f'Question "{tf_question}..." supprimée.')
        return redirect('teacher:tf_list_by_unite', unite_id=unite.id)
    
    context = {
        'tf': tf,
        'chapitre': chapitre,
        'unite': unite,
        'title': 'Supprimer la question',
    }
    
    return render(request, 'teacher/quizzes/tf/supprimer.html', context)
