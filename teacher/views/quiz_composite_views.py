from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from lecon.models import Unite, Chapter
from quizzes.models import MCQQuiz, QAQuiz, MCQ, QuestionAnswer
from ..decorators import teacher_required, teacher_of_unite_required
from ..forms import MCQQuizForm, QAQuizForm


# ==================== MCQ QUIZ ====================

@login_required
@teacher_required
def mcq_quiz_list(request, unite_id=None):
    """
    Liste des quiz QCM
    unite_id est optionnel - si fourni, filtre par unité
    """
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    # Base queryset
    quizzes = MCQQuiz.objects.filter(subject__in=teaching_unites).select_related('subject')
    qa_quizzes = QAQuiz.objects.filter(subject__in=teaching_unites).select_related('subject')
    
    unite = None
    if unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite in teaching_unites:
            quizzes = quizzes.filter(subject=unite)
            qa_quizzes = qa_quizzes.filter(subject=unite)
    
    # Filtrage par statut
    status = request.GET.get('status')
    now = timezone.now()
    
    if status == 'active':
        quizzes = quizzes.filter(start_date__lte=now, end_date__gte=now)
        qa_quizzes = qa_quizzes.filter(start_date__lte=now, end_date__gte=now)
    elif status == 'upcoming':
        quizzes = quizzes.filter(start_date__gt=now)
        qa_quizzes = qa_quizzes.filter(start_date__gt=now)
    elif status == 'past':
        quizzes = quizzes.filter(end_date__lt=now)
        qa_quizzes = qa_quizzes.filter(end_date__lt=now)
    
    context = {
        'quizzes': quizzes,
        'qa_quizzes': qa_quizzes,
        'unite': unite,
        'teaching_unites': teaching_unites,
        'status': status,
    }
    
    return render(request, 'teacher/quizzes/composite/liste.html', context)


@login_required
@teacher_required
def mcq_quiz_create(request, unite_id):
    """Créer un quiz QCM"""
    unite = get_object_or_404(Unite, pk=unite_id)
    
    # Vérifier que l'enseignant a accès à cette unité
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à cette unité.')
        return redirect('teacher:mcq_quiz_list')
    
    if request.method == 'POST':
        form = MCQQuizForm(request.POST, teacher=request.user, unite_id=unite_id)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = unite
            quiz.save()
            form.save_m2m()
            messages.success(request, f'Quiz "{quiz.title}" créé avec succès.')
            return redirect('teacher:mcq_quiz_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = MCQQuizForm(teacher=request.user, unite_id=unite_id)
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Créer un quiz QCM - {unite.title}',
        'button_text': 'Créer',
        'quiz_type': 'mcq',
    }
    
    return render(request, 'teacher/quizzes/composite/formulaire.html', context)


@login_required
@teacher_required
def mcq_quiz_edit(request, pk):
    """Modifier un quiz QCM"""
    quiz = get_object_or_404(MCQQuiz, pk=pk)
    unite = quiz.subject
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:mcq_quiz_list')
    
    if request.method == 'POST':
        form = MCQQuizForm(request.POST, instance=quiz, teacher=request.user, unite_id=unite.id)
        if form.is_valid():
            form.save()
            messages.success(request, f'Quiz "{quiz.title}" modifié avec succès.')
            return redirect('teacher:mcq_quiz_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = MCQQuizForm(instance=quiz, teacher=request.user, unite_id=unite.id)
    
    context = {
        'form': form,
        'quiz': quiz,
        'unite': unite,
        'title': f'Modifier - {quiz.title}',
        'button_text': 'Enregistrer',
        'quiz_type': 'mcq',
    }
    
    return render(request, 'teacher/quizzes/composite/formulaire.html', context)


@login_required
@teacher_required
def mcq_quiz_delete(request, pk):
    """Supprimer un quiz QCM"""
    quiz = get_object_or_404(MCQQuiz, pk=pk)
    unite = quiz.subject
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:mcq_quiz_list')
    
    if request.method == 'POST':
        quiz_title = quiz.title
        quiz.delete()
        messages.success(request, f'Quiz "{quiz_title}" supprimé avec succès.')
        return redirect('teacher:mcq_quiz_list')
    
    context = {
        'quiz': quiz,
        'unite': unite,
        'title': f'Supprimer {quiz.title}',
    }
    
    return render(request, 'teacher/quizzes/composite/supprimer.html', context)


# ==================== QA QUIZ ====================

@login_required
@teacher_required
def qa_quiz_list(request, unite_id=None):
    """
    Liste des quiz QA
    unite_id est optionnel - si fourni, filtre par unité
    """
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    quizzes = QAQuiz.objects.filter(subject__in=teaching_unites).select_related('subject')
    
    unite = None
    if unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite in teaching_unites:
            quizzes = quizzes.filter(subject=unite)
    
    status = request.GET.get('status')
    now = timezone.now()
    
    if status == 'active':
        quizzes = quizzes.filter(start_date__lte=now, end_date__gte=now)
    elif status == 'upcoming':
        quizzes = quizzes.filter(start_date__gt=now)
    elif status == 'past':
        quizzes = quizzes.filter(end_date__lt=now)
    
    context = {
        'quizzes': quizzes,
        'unite': unite,
        'teaching_unites': teaching_unites,
        'status': status,
        'quiz_type': 'qa',
    }
    
    return render(request, 'teacher/quizzes/composite/qa_liste.html', context)


@login_required
@teacher_required
def qa_quiz_create(request, unite_id):
    """Créer un quiz QA"""
    unite = get_object_or_404(Unite, pk=unite_id)
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_quiz_list')
    
    if request.method == 'POST':
        form = QAQuizForm(request.POST, teacher=request.user, unite_id=unite_id)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = unite
            quiz.save()
            form.save_m2m()
            messages.success(request, f'Quiz "{quiz.title}" créé avec succès.')
            return redirect('teacher:qa_quiz_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = QAQuizForm(teacher=request.user, unite_id=unite_id)
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Créer un quiz QA - {unite.title}',
        'button_text': 'Créer',
        'quiz_type': 'qa',
    }
    
    return render(request, 'teacher/quizzes/composite/formulaire.html', context)


@login_required
@teacher_required
def qa_quiz_edit(request, pk):
    """Modifier un quiz QA"""
    quiz = get_object_or_404(QAQuiz, pk=pk)
    unite = quiz.subject
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_quiz_list')
    
    if request.method == 'POST':
        form = QAQuizForm(request.POST, instance=quiz, teacher=request.user, unite_id=unite.id)
        if form.is_valid():
            form.save()
            messages.success(request, f'Quiz "{quiz.title}" modifié avec succès.')
            return redirect('teacher:qa_quiz_list_by_unite', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = QAQuizForm(instance=quiz, teacher=request.user, unite_id=unite.id)
    
    context = {
        'form': form,
        'quiz': quiz,
        'unite': unite,
        'title': f'Modifier - {quiz.title}',
        'button_text': 'Enregistrer',
        'quiz_type': 'qa',
    }
    
    return render(request, 'teacher/quizzes/composite/formulaire.html', context)


@login_required
@teacher_required
def qa_quiz_delete(request, pk):
    """Supprimer un quiz QA"""
    quiz = get_object_or_404(QAQuiz, pk=pk)
    unite = quiz.subject
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:qa_quiz_list')
    
    if request.method == 'POST':
        quiz_title = quiz.title
        quiz.delete()
        messages.success(request, f'Quiz "{quiz_title}" supprimé avec succès.')
        return redirect('teacher:qa_quiz_list')
    
    context = {
        'quiz': quiz,
        'unite': unite,
        'title': f'Supprimer {quiz.title}',
    }
    
    return render(request, 'teacher/quizzes/composite/supprimer.html', context)


