from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Count, Sum, Q
from django.core.paginator import Paginator
from .models import Unite, Chapter, UniteSection
from subscriptions.models import Subscription, SubscriptionUsageAudit
from subscriptions.decorators import student_required, active_subscription_required
from quizzes.models import MCQResult, QAResult, TrueFalseResult, MCQAttempt, QAAttempt
from lessoncopy.models import StudySession, Resume, ResumeIA
from quizlet_copy.models import FlashcardSet, Flashcard, UserProgress  # assuming this app exists
import json
from quizzes.models import MCQ, QuestionAnswer, TrueFalseQuiz
from django.db.models import Prefetch


@login_required
@student_required
@active_subscription_required()
def subject_list(request):
    """
    Liste des unités d'enseignement accessibles à l'étudiant (filtrées par niveau)
    """
    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)

    # Efficiently prefetch only active chapters for each subject
    active_chapters_prefetch = Prefetch(
        'chapters',
        queryset=Chapter.objects.filter(is_active=True).order_by('order'),
        to_attr='active_chapters'  # Stores result in subject.active_chapters
    )

    subjects = Unite.objects.filter(
        level=profile.level
    ).annotate(
        active_chapter_count=Count('chapters', filter=Q(chapters__is_active=True))
    ).order_by('title')


    # Optional: log list view
    SubscriptionUsageAudit.log_usage(
        action_type='feature_access',
        details={'feature': 'view_subject_list', 'count': subjects.count()},
        request=request,
        subscription=active_sub,
        student=profile
    )

    context = {
        'subjects': subjects,
        'active_subscription': active_sub,
        'profile': profile,
    }
    return render(request, 'lecon/subject_list.html', context)

  
@login_required
@student_required
@active_subscription_required()
def subject_detail(request, pk):
    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    unite = get_object_or_404(Unite, pk=pk)

    # 🔐 Security check
    if unite.level != profile.level:
        messages.error(request, "Cette unité d'enseignement n'est pas disponible pour votre niveau d'études.")
        return redirect('lecon:subject_list')
 
    # ✅ Get ONLY active chapters (as a queryset - reusable for all filters)
    active_chapters = unite.chapters.filter(is_active=True).order_by('order')
    sections = UniteSection.objects.filter(ue=unite)

    # 📊 Statistics - filtered to active chapters ONLY
    # Use chapter__in=active_chapters (not chapter_id__in)
    total_mcqs = MCQ.objects.filter(chapter__in=active_chapters).count()
    total_qas  = QuestionAnswer.objects.filter(chapter__in=active_chapters).count()
    total_tfs  = TrueFalseQuiz.objects.filter(chapter__in=active_chapters).count()

    # Student-specific stats (active chapters only)
    total_study_seconds = StudySession.objects.filter(
        user=request.user,
        chapter__in=active_chapters,
        completed=True
    ).aggregate(total=Sum('duration_seconds'))['total'] or 0

    total_study_hours = total_study_seconds // 3600
    total_study_minutes = (total_study_seconds % 3600) // 60

    # Average scores (active chapters only)
    mcq_avg = MCQResult.objects.filter(
        student=request.user, 
        chapter__in=active_chapters
    ).aggregate(Avg('score'))['score__avg'] or 0
    
    qa_avg  = QAResult.objects.filter(
        student=request.user, 
        chapter__in=active_chapters
    ).aggregate(Avg('score'))['score__avg'] or 0
    
    tf_avg  = TrueFalseResult.objects.filter(
        student=request.user, 
        chapter__in=active_chapters
    ).aggregate(Avg('score'))['score__avg'] or 0

    # ⚠️ Quiz-level attempts (MCQQuiz/QAQuiz have M2M to Chapter)
    mcq_quiz_avg = MCQAttempt.objects.filter(
        student=request.user, 
        quiz__chapters__in=active_chapters  # ✅ MCQAttempt → MCQQuiz → chapters (M2M)
    ).aggregate(Avg('score'))['score__avg'] or 0
    
    qa_quiz_avg = QAAttempt.objects.filter(
        student=request.user, 
        quiz__chapters__in=active_chapters  # ✅ QAAttempt → QAQuiz → chapters (M2M)
    ).aggregate(Avg('score'))['score__avg'] or 0

    # 🃏 Flashcards - filtered to active chapters + annotate card count
    flashcard_sets_public = FlashcardSet.objects.filter(
        title__in=active_chapters,  # ⚠️ Your FK field is named 'title'
        is_public=True
    ).annotate(card_count=Count('cards')).order_by('-created_at')
    
    if not active_sub.feature.can_view_public_flashcard:
        flashcard_sets_public = flashcard_sets_public.none()
        messages.info(request, "Les cartes mentales publiques nécessitent un abonnement.")
    
    flashcard_sets_private = FlashcardSet.objects.filter(
        title__in=active_chapters,
        is_public=False, 
        created_by=request.user
    ).annotate(card_count=Count('cards')).order_by('-created_at')
    
    if not active_sub.feature.can_add_own_flashcard:
        flashcard_sets_private = flashcard_sets_private.none()
        messages.info(request, "Votre abonnement actuel ne vous permet pas de créer et voir des cartes mentales personnelles.")


    if not active_sub.feature.can_view_public_flashcard:
        flashcard_sets_public = flashcard_sets_public.none()
        messages.info(request, "Les cartes mentales publiques nécessitent un abonnement.")
    

    # Annotate chapters with flashcard counts and study time
    chapters_flashcard = active_chapters.annotate(
        flashcards_count=Count('flashcardset__cards', distinct=True),
        study_seconds=Sum(
            'studysession__duration_seconds',
            filter=Q(studysession__user=request.user, studysession__completed=True)
        )
    ).order_by('order')

    # Calculate derived values for template
    for chapter in chapters_flashcard:
        chapter.study_hours = (chapter.study_seconds or 0) // 3600
        chapter.study_minutes = ((chapter.study_seconds or 0) % 3600) // 60

    # Calculate total flashcards
    total_flashcards = FlashcardSet.objects.filter(
        Q(title__in=active_chapters, is_public=True) | 
        Q(title__in=active_chapters, is_public=False, created_by=request.user)
    ).aggregate(total=Count('cards'))['total'] or 0

    # Add to context
    context = {
        # 'chapters_flashcard': chapters_flashcard,  # Now with annotations
        'total_flashcards': total_flashcards,
        'unite': unite,
        'chapters': active_chapters,
        'sections': sections,
        'total_mcqs': total_mcqs,
        'total_qas': total_qas,
        'total_tfs': total_tfs,
        'total_study_hours': total_study_hours,
        'total_study_minutes': total_study_minutes,
        'mcq_score': round(mcq_avg, 1),
        'qa_score': round(qa_avg, 1),
        'tf_score': round(tf_avg, 1),
        'mcq_quiz_score': round(mcq_quiz_avg, 1),
        'qa_quiz_score': round(qa_quiz_avg, 1),
        'active_subscription': active_sub,
        'can_view_flashcards': active_sub.feature.can_view_public_flashcard,
        'flashcard_sets_public': flashcard_sets_public,
        'flashcard_sets_private': flashcard_sets_private,

    }
    return render(request, 'lecon/student/subject_detail.html', context)

 
@login_required
@student_required
@active_subscription_required()
def chapter_detail(request, subject_pk, chapter_pk):
    unite = get_object_or_404(Unite, id=subject_pk)
    chapter = get_object_or_404(Chapter, pk=chapter_pk, ue__pk=subject_pk)
    
    # Get all related content
    mcqs = chapter.mcq_set.all()
    qas = chapter.questionanswer_set.all()
    lessons = chapter.copy_set.all()
    document = chapter.importer_set.all()
    tfs = chapter.truefalsequiz_set.all()
    
    # Get Flashcard Sets for this chapter
    flashcard_sets = FlashcardSet.objects.filter(title=chapter, created_by=request.user)
    flashcard_sets_private = FlashcardSet.objects.filter(title=chapter, created_by=request.user, is_public=False)
    flashcard_sets_public = FlashcardSet.objects.filter(title=chapter, is_public=True)
    
    # Get user's flashcard progress
    user_flashcard_progress = None
    total_flashcards = 0
    mastered_flashcards = 0
    
    if request.user.is_authenticated:
        # Calculate flashcard progress
        flashcards = Flashcard.objects.filter(flashcard_set__title=chapter)
        total_flashcards = flashcards.count()
        
        if total_flashcards > 0:
            user_progress = UserProgress.objects.filter(
                user=request.user,
                flashcard__in=flashcards
            )
            mastered_flashcards = user_progress.filter(mastered=True).count()
            user_flashcard_progress = {
                'total': total_flashcards,
                'mastered': mastered_flashcards,
                'percentage': (mastered_flashcards / total_flashcards * 100) if total_flashcards > 0 else 0,
                'in_progress': user_progress.filter(mastered=False).count()
            }
    
    # Get AI Resume
    ai_resume = ResumeIA.objects.filter(chapitre=chapter).first()
    
    # Get User Resume (only for the current user)
    user_resume = Resume.objects.filter(chapitre=chapter, createur=request.user).first()
    
    # Study time for this chapter
    study_time_seconds = 0
    if request.user.is_student:
        study_sessions = StudySession.objects.filter(
            user=request.user,
            chapter=chapter,
            completed=True
        )
        study_time_seconds = sum(session.duration_seconds for session in study_sessions)
    
    context = {
        'unite': unite,
        'chapter': chapter,
        'mcqs': mcqs,
        'qas': qas,
        'lessons': lessons,
        'document': document,
        'tfs': tfs,
        'ai_resume': ai_resume,
        'user_resume': user_resume,
        'flashcard_sets': flashcard_sets,
        'flashcard_sets': flashcard_sets,
        'flashcard_sets_private': flashcard_sets_private,
        'flashcard_sets_public': flashcard_sets_public,
        'user_flashcard_progress': user_flashcard_progress,
        'study_time_hours': study_time_seconds // 3600,
        'study_time_minutes': (study_time_seconds % 3600) // 60,
    }
    
    return render(request, 'lecon/student/chapter_detail.html', context)

