from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .models import (
    MCQ, MCQResult,
    MCQQuiz, MCQAttempt,
    QuestionAnswer, QAAnswer, QAResult, QAQuiz, QAAttempt,
    TrueFalseQuiz, TrueFalseResult, StudentAnswer
)
from lecon.models import Chapter
from subscriptions.models import Subscription, SubscriptionUsageAudit
from subscriptions.decorators import student_required, active_subscription_required
from .utils import similarity_analyzer  # for QA scoring
from lecon.models import Chapter, Unite
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def _get_remaining_attempts(profile, quiz_type, is_formal_exam=False):
    """
    Returns (remaining_count, active_subscription)
    
    Parameters:
    - quiz_type: 'mcq', 'qa', 'tf' (for chapter quizzes) or 'mcq_exam', 'qa_exam' (for formal exams)
    - is_formal_exam: True for formal exams, False for chapter quizzes
    """
    active_sub = Subscription.get_student_active_subscription(profile)
    if not active_sub:
        return 0, None

    # Map quiz types to subscription fields
    if is_formal_exam:
        if quiz_type == 'mcq_exam':
            max_allowed = active_sub.feature.mcq_exam_feature
            used_field = 'mcq_exam_attempts_used'
        elif quiz_type == 'qa_exam':
            max_allowed = active_sub.feature.qa_exam_feature
            used_field = 'qa_exam_attempts_used'
        else:
            return 0, active_sub
    else:
        if quiz_type == 'mcq':
            max_allowed = active_sub.feature.mcq_features
            used_field = 'mcq_attempts_used'
        elif quiz_type == 'qa':
            max_allowed = active_sub.feature.qa_features
            used_field = 'qa_attempts_used'
        elif quiz_type == 'tf':
            max_allowed = active_sub.feature.tf_features
            used_field = 'tf_attempts_used'
        else:
            return 0, active_sub

    if max_allowed <= 0:
        return 0, active_sub

    # Get used attempts directly from subscription
    used = getattr(active_sub, used_field, 0)
    remaining = max(0, max_allowed - used)
    
    return remaining, active_sub


def _record_attempt(subscription, quiz_type, is_formal_exam=False):
    """Record an attempt in the subscription"""
    if is_formal_exam:
        if quiz_type == 'mcq_exam':
            subscription.record_mcq_exam_attempt()
        elif quiz_type == 'qa_exam':
            subscription.record_qa_exam_attempt()
    else:
        if quiz_type == 'mcq':
            subscription.record_mcq_attempt()
        elif quiz_type == 'qa':
            subscription.record_qa_attempt()
        elif quiz_type == 'tf':
            subscription.record_tf_attempt()


@student_required
@active_subscription_required()
def start_mcq(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    profile = request.user.student_profile

    remaining, active_sub = _get_remaining_attempts(profile, quiz_type='mcq', is_formal_exam=False)
    if remaining <= 0:
        messages.warning(
            request,
            f"Limite de tentatives MCQ atteinte ({active_sub.feature.mcq_features})."
        )
        return redirect('subscriptions:create_subscription')

    questions = chapter.mcq_set.all().order_by('?')[:10]
    if not questions.exists():
        messages.info(request, "Aucune question MCQ disponible.")
        return redirect('lecon:chapter_detail_student', subject_pk=chapter.ue.id, chapter_pk=chapter.id) 

    # Store question IDs in session for later retrieval
    request.session['mcq_question_ids'] = [q.id for q in questions]

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_start',
        details={'type': 'mcq_chapter', 'chapter_id': chapter.id, 'remaining': remaining - 1},
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'quizzes/mcqs/mcq.html', {
        'chapter': chapter,
        'questions': questions,
    })


@student_required
@active_subscription_required()
def start_qa(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    profile = request.user.student_profile

    remaining, active_sub = _get_remaining_attempts(profile, quiz_type='qa', is_formal_exam=False)
    if remaining <= 0:
        messages.warning(
            request,
            f"Limite de tentatives Q&A atteinte ({active_sub.feature.qa_features})."
        )
        return redirect('subscriptions:create_subscription')

    questions = chapter.questionanswer_set.all().order_by('?')[:2]
    if not questions.exists():
        messages.info(request, "Aucune question QA disponible.")
        return redirect('lecon:chapter_detail', unite_pk=chapter.ue.id, chapter_pk=chapter.id)

    request.session['qa_question_ids'] = [q.id for q in questions]
    request.session['qa_chapter_id'] = chapter_id

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_start',
        details={'type': 'qa_chapter', 'chapter_id': chapter.id, 'remaining': remaining - 1},
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'quizzes/qas/qa.html', {
        'chapter': chapter,
        'questions': questions,
    })


@student_required
@active_subscription_required()
def start_tf(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    profile = request.user.student_profile

    remaining, active_sub = _get_remaining_attempts(profile, quiz_type='tf', is_formal_exam=False)
    if remaining <= 0:
        messages.warning(
            request,
            f"Limite de tentatives Vrai/Faux atteinte ({active_sub.feature.tf_features})."
        )
        return redirect('subscriptions:create_subscription')

    questions = chapter.truefalsequiz_set.all().order_by('?')[:10]
    if not questions.exists():
        messages.info(request, "Aucune question Vrai/Faux disponible.")
        return redirect('lecon:chapter_detail', unite_pk=chapter.ue.id, chapter_pk=chapter.id)

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_start',
        details={'type': 'tf_chapter', 'chapter_id': chapter.id, 'remaining': remaining - 1},
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'quizzes/tfs/start_tf.html', {
        'chapter': chapter,
        'questions': questions,
    })


@student_required
@active_subscription_required()
def start_mcq_quiz(request, quiz_id):
    quiz = get_object_or_404(MCQQuiz, pk=quiz_id)
    profile = request.user.student_profile

    remaining, active_sub = _get_remaining_attempts(profile, quiz_type='mcq_exam', is_formal_exam=True)
    if remaining <= 0:
        messages.warning(
            request,
            f"Limite d'examens MCQ atteinte ({active_sub.feature.mcq_exam_feature})."
        )
        return redirect('subscriptions:create_subscription')

    attempts_count = MCQAttempt.objects.filter(quiz=quiz, student=profile.user).count()
    if attempts_count >= quiz.max_attempts:
        messages.error(request, f"Vous avez épuisé les {quiz.max_attempts} tentatives pour ce quiz.")
        return redirect('lecon:subject_detail', pk=quiz.subject.id)

    attempt = MCQAttempt.objects.create(
        quiz=quiz,
        student=profile.user,
        score=0,
        completed=False
    )

    SubscriptionUsageAudit.log_usage(
        action_type='exam_start',
        details={'type': 'mcq_exam', 'quiz_id': quiz.id, 'remaining': remaining - 1},
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'quizzes/mcqs/mcq_quiz.html', {
        'quiz': quiz,
        'attempt': attempt,
        'questions': quiz.questions.all().order_by('?')[:10],
    })


@student_required
@active_subscription_required()
def start_qa_quiz(request, quiz_id):
    quiz = get_object_or_404(QAQuiz, pk=quiz_id)
    profile = request.user.student_profile

    remaining, active_sub = _get_remaining_attempts(profile, quiz_type='qa_exam', is_formal_exam=True)
    if remaining <= 0:
        messages.warning(
            request,
            f"Limite d'examens Q&A atteinte ({active_sub.feature.qa_exam_feature})."
        )
        return redirect('subscriptions:create_subscription')

    attempts_count = QAAttempt.objects.filter(quiz=quiz, student=profile.user).count()
    if attempts_count >= quiz.max_attempts:
        messages.error(request, f"Vous avez épuisé les {quiz.max_attempts} tentatives pour ce quiz.")
        return redirect('lecon:subject_detail', pk=quiz.subject.id)

    attempt = QAAttempt.objects.create(
        quiz=quiz,
        student=profile.user,
        score=None,
        completed=False,
        answers={}
    )

    SubscriptionUsageAudit.log_usage(
        action_type='exam_start',
        details={'type': 'qa_exam', 'quiz_id': quiz.id, 'remaining': remaining - 1},
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'quizzes/qas/qa_quiz.html', {
        'quiz': quiz,
        'attempt': attempt,
        'questions': quiz.questions.all(),
    })


# ────────────────────────────────────────────────
#   SUBMIT VIEWS — with completion logging and attempt recording
# ────────────────────────────────────────────────

@student_required
@active_subscription_required()
def submit_mcq(request, chapter_id):
    """
    Process MCQ chapter quiz submission → save result + log completion + record attempt
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    if request.method != 'POST':
        return redirect('quizzes:start_mcq', chapter_id=chapter_id)

    # Retrieve questions that were presented
    question_ids = request.session.get('mcq_question_ids', [])
    if not question_ids:
        messages.error(request, "Session expirée. Veuillez recommencer le quiz.")
        return redirect('quizzes:start_mcq', chapter_id=chapter_id)

    questions = MCQ.objects.filter(id__in=question_ids, chapter=chapter)

    if not questions.exists():
        messages.error(request, "Les questions n'ont pas pu être récupérées.")
        return redirect('lecon:chapter_detail', unite_pk=chapter.ue.id, chapter_pk=chapter.id)

    correct = 0
    total = len(questions)
    user_answers = {}
    
    # Create a list to store question data with user answers
    questions_with_answers = []

    for question in questions:
        selected = request.POST.get(f'question_{question.id}')
        if selected is not None:
            selected = int(selected)
            user_answers[question.id] = selected
            if selected == question.correct_option:
                correct += 1
        
        # Add user's answer to the question object or create a dict
        question.user_answer = user_answers.get(question.id)
        questions_with_answers.append(question)

    score = (correct / total * 100) if total > 0 else 0

    # Save result
    MCQResult.objects.create(
        student=request.user,
        chapter=chapter,
        score=score
    )

    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    
    # Record the MCQ attempt in subscription
    try:
        active_sub.record_mcq_attempt()
    except Exception as e:
        messages.error(request, f"Erreur lors de l'enregistrement de la tentative: {str(e)}")

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_complete',
        details={
            'type': 'mcq_chapter',
            'chapter_id': chapter.id,
            'score': round(score, 2),
            'correct': correct,
            'total': total,
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    # Clear session
    request.session.pop('mcq_question_ids', None)

    context = {
        'chapter': chapter,
        'score': round(score, 1),
        'correct': correct,
        'total': total,
        'questions': questions_with_answers,  # Use the updated list
        'user_answers': user_answers,
    }
    
    print ("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    print('questions_with_answers:', [(q.id, q.user_answer) for q in questions_with_answers])
    print('user_answers dict:', user_answers)
    print ("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    return render(request, 'quizzes/mcqs/mcq_result.html', context)



@student_required
@active_subscription_required()
def submit_qa(request, chapter_id):
    """
    Process QA chapter quiz submission → similarity scoring + log completion + record attempt
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    if request.method != 'POST':
        return redirect('quizzes:start_qa', chapter_id=chapter_id)

    question_ids = request.session.get('qa_question_ids', [])
    if not question_ids:
        messages.error(request, "Session expirée. Veuillez recommencer le quiz.")
        return redirect('quizzes:start_qa', chapter_id=chapter_id)

    questions = QuestionAnswer.objects.filter(id__in=question_ids, chapter=chapter)

    total_similarity = 0
    answered_count = 0
    detailed_results = []

    for question in questions:
        answer_key = f'question_{question.id}'
        student_answer = request.POST.get(answer_key, '').strip()

        if student_answer:
            try:
                similarity = similarity_analyzer.calculate_similarity(
                    student_answer,
                    question.sample_answer or "",
                    method='auto'
                )
                total_similarity += similarity
                answered_count += 1

                detailed_results.append({
                    'question': question.question,
                    'student_answer': student_answer,
                    'sample_answer': question.sample_answer or "Non fourni",
                    'similarity': round(similarity * 100, 1),  # in %
                })

                # Save individual answer
                QAAnswer.objects.create(
                    chapter=chapter,
                    question=question,
                    student=request.user,
                    answer=student_answer,
                )

            except Exception as e:
                print(f"Erreur QA pour question {question.id}: {e}")

    avg_similarity = (total_similarity / answered_count * 100) if answered_count > 0 else 0

    # Save overall result
    QAResult.objects.create(
        chapter=chapter,
        student=request.user,
        score=avg_similarity
    )

    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    
    # Record the QA attempt in subscription
    try:
        active_sub.record_qa_attempt()
    except Exception as e:
        messages.error(request, f"Erreur lors de l'enregistrement de la tentative: {str(e)}")

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_complete',
        details={
            'type': 'qa_chapter',
            'chapter_id': chapter.id,
            'score': round(avg_similarity, 2),
            'answered': answered_count,
            'total': len(questions),
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    # Clear session
    request.session.pop('qa_question_ids', None)
    request.session.pop('qa_chapter_id', None)

    context = {
        'chapter': chapter,
        'score': round(avg_similarity, 1),
        'detailed_results': detailed_results,
        'answered': answered_count,
        'total': len(questions),
    }

    return render(request, 'quizzes/qas/qa_result.html', context)


@student_required
@active_subscription_required()
def submit_tf(request, chapter_id):
    """
    Process True/False chapter quiz submission → simple scoring + log completion + record attempt
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    if request.method != 'POST':
        return redirect('quizzes:start_tf', chapter_id=chapter_id)

    # Get question IDs from the POST data
    question_ids = []
    for key in request.POST.keys():
        if key.startswith('question_'):
            q_id = key.split('_')[1]
            try:
                question_ids.append(int(q_id))
            except ValueError:
                continue

    questions = TrueFalseQuiz.objects.filter(id__in=question_ids, chapter=chapter)

    correct = 0
    total = len(questions)
    user_answers = {}
    
    # Prepare questions with user answers
    questions_with_data = []

    for question in questions:
        user_choice_str = request.POST.get(f'question_{question.id}')
        user_choice = user_choice_str == 'True' if user_choice_str else None
        
        # Calculate if answer is correct
        is_correct = False
        if user_choice is not None:
            user_answers[question.id] = user_choice
            if user_choice == question.answer:
                correct += 1
                is_correct = True
        
        # Create a simple object/dict with all needed data
        question_data = {
            'id': question.id,
            'question': question.question,
            'answer': question.answer,
            'user_answer': user_choice,
            'is_correct': is_correct,
            'explanation': question.explanation,
        }
        questions_with_data.append(question_data)

    score = (correct / total * 100) if total > 0 else 0

    # Save result
    TrueFalseResult.objects.create(
        chapter=chapter,
        student=request.user,
        score=score
    )

    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    
    # Record the TF attempt in subscription
    try:
        active_sub.record_tf_attempt()
    except Exception as e:
        messages.error(request, f"Erreur lors de l'enregistrement de la tentative: {str(e)}")

    SubscriptionUsageAudit.log_usage(
        action_type='quiz_complete',
        details={
            'type': 'tf_chapter',
            'chapter_id': chapter.id,
            'score': round(score, 2),
            'correct': correct,
            'total': total,
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    context = {
        'chapter': chapter,
        'score': round(score, 1),
        'correct': correct,
        'total': total,
        'questions': questions_with_data,  # Pass the enriched data
        'user_answers': user_answers,
    }
    
    # Debug print
    print("TF Quiz Results:")
    print(f"Score: {score}%")
    print(f"Correct: {correct}/{total}")
    print("Questions data:", [(q['id'], q['answer'], q['user_answer'], q['is_correct']) for q in questions_with_data])

    return render(request, 'quizzes/tfs/tf_result.html', context)


@student_required
@active_subscription_required()
def submit_mcq_quiz(request, attempt_id):
    """
    Submit formal MCQ quiz attempt → update score + mark completed + log + record attempt
    """
    attempt = get_object_or_404(MCQAttempt, id=attempt_id, student=request.user, completed=False)

    quiz = attempt.quiz

    if request.method != 'POST':
        return redirect('quizzes:start_mcq_quiz', quiz_id=quiz.id)

    correct = 0
    total = quiz.questions.count()

    for question in quiz.questions.all():
        selected = request.POST.get(f'question_{question.id}')
        if selected is not None and int(selected) == question.correct_option:
            correct += 1

    score = (correct / total * 100) if total > 0 else 0

    attempt.score = score
    attempt.completed = True
    attempt.end_time = timezone.now()
    attempt.save()

    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    
    # Record the MCQ exam attempt in subscription
    try:
        active_sub.record_mcq_exam_attempt()
    except Exception as e:
        messages.error(request, f"Erreur lors de l'enregistrement de la tentative: {str(e)}")

    SubscriptionUsageAudit.log_usage(
        action_type='exam_complete',
        details={
            'type': 'mcq_exam',
            'quiz_id': quiz.id,
            'score': round(score, 2),
            'correct': correct,
            'total': total,
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    context = {
        'quiz': quiz,
        'attempt': attempt,
        'score': round(score, 1),
        'correct': correct,
        'total': total,
    }

    return render(request, 'quizzes/mcqs/mcq_quiz_result.html', context)


@student_required
@active_subscription_required()
def submit_qa_quiz(request, attempt_id):
    """
    Submit formal QA quiz attempt → save answers + log completion + record attempt
    """
    attempt = get_object_or_404(QAAttempt, id=attempt_id, student=request.user, completed=False)

    quiz = attempt.quiz

    if request.method != 'POST':
        return redirect('quizzes:start_qa_quiz', quiz_id=quiz.id)

    answers_data = {}
    for question in quiz.questions.all():
        key = f'question_{question.id}'
        answer = request.POST.get(key, '').strip()
        if answer:
            answers_data[question.id] = answer

            # Optional: immediate similarity (for feedback)
            similarity = similarity_analyzer.calculate_similarity(
                answer, question.sample_answer or "", method='auto'
            ) if question.sample_answer else 0

            StudentAnswer.objects.create(
                attempt=attempt,
                question=question,
                answer=answer,
                similarity_score=similarity
            )

    attempt.answers = answers_data
    attempt.completed = True
    attempt.end_time = timezone.now()
    # attempt.score remains None or auto-calculated if you want
    attempt.save()

    profile = request.user.student_profile
    active_sub = Subscription.get_student_active_subscription(profile)
    
    # Record the QA exam attempt in subscription
    try:
        active_sub.record_qa_exam_attempt()
    except Exception as e:
        messages.error(request, f"Erreur lors de l'enregistrement de la tentative: {str(e)}")

    SubscriptionUsageAudit.log_usage(
        action_type='exam_complete',
        details={
            'type': 'qa_exam',
            'quiz_id': quiz.id,
            'answered_count': len(answers_data),
            'total_questions': quiz.questions.count(),
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    messages.success(request, "Vos réponses ont été enregistrées. Le score sera disponible après correction.")
    return redirect('lecon:subject_detail', pk=quiz.subject.id)


@active_subscription_required()
@login_required
def list_subject_mcq_quizzes(request, subject_pk):
    """List all MCQ quizzes for a subject or all subjects"""
    now = timezone.now()
    
    subject = Unite.objects.filter(id=subject_pk).first()
    mcq_quizzes = MCQQuiz.objects.filter(subject=subject).order_by('-created_at')

    if request.user.is_student:
        subject = Unite.objects.filter(id=subject_pk,
            level=request.user.level_of_study,
            enrollmentrequest__student=request.user
        ).first()
        mcq_quizzes = MCQQuiz.objects.filter(
            subject=subject,
            end_date__gte=now
        ).order_by('-start_date')

    
    # Initialize statistics
    user_attempts_count = 0
    total_attempts_possible = 0
    total_score = 0
    scored_attempts_count = 0
    active_quizzes_count = 0
    
    # Process each quiz
    for quiz in mcq_quizzes:
        # Calculate availability
        quiz.is_available = quiz.start_date <= now <= quiz.end_date
        if quiz.is_available:
            active_quizzes_count += 1
        
        if request.user.is_authenticated:
            # Get user attempts for this quiz
            attempts = MCQAttempt.objects.filter(
                quiz=quiz, 
                student=request.user
            )
            quiz.user_attempts = attempts.count()
            quiz.can_attempt = quiz.user_attempts < quiz.max_attempts
            
            # Update statistics
            user_attempts_count += quiz.user_attempts
            total_attempts_possible += quiz.max_attempts
            
            # Calculate scores for this quiz
            for attempt in attempts:
                if attempt.score is not None:
                    total_score += attempt.score
                    scored_attempts_count += 1
        else:
            quiz.user_attempts = 0
            quiz.can_attempt = False
    
    # Calculate participation rate (avoid division by zero)
    participation_rate = 0
    if total_attempts_possible > 0:
        participation_rate = (user_attempts_count / total_attempts_possible) * 100
    
    # Calculate average score (avoid division by zero)
    average_score = 0
    if scored_attempts_count > 0:
        average_score = total_score / scored_attempts_count
    
    # Get total quiz count (for pagination)
    total_quizzes_count = mcq_quizzes.count()
    
    # Pagination
    paginator = Paginator(mcq_quizzes, 12)
    page_number = request.GET.get('page')
    try:
        mcq_quizzes = paginator.page(page_number)
    except PageNotAnInteger:
        mcq_quizzes = paginator.page(1)
    except EmptyPage:
        mcq_quizzes = paginator.page(paginator.num_pages)
    
    context = {
        'mcq_quizzes': mcq_quizzes,
        'subject': subject,
        'now': now,
        'user_attempts_count': user_attempts_count,
        'total_attempts_possible': total_attempts_possible,
        'participation_rate': participation_rate,
        'average_score': average_score,
        'active_quizzes_count': active_quizzes_count,
        'total_quizzes_count': total_quizzes_count,
    }
    
    return render(request, 'quizzes/mcqs/list_subject_mcq_quizzes.html', context)


@active_subscription_required()
@login_required
def list_subject_qa_quizzes(request, subject_pk):
    """List all MCQ quizzes for a subject or all subjects"""
    now = timezone.now()
    
    subject = Unite.objects.filter(id=subject_pk).first()
    qa_quizzes = QAQuiz.objects.filter(subject=subject).order_by('-created_at')

    if request.user.is_student:
        subject = Unite.objects.filter(id=subject_pk,
            level=request.user.level_of_study,
            enrollmentrequest__student=request.user
        ).first()
        qa_quizzes = QAQuiz.objects.filter(
            subject=subject,
            end_date__gte=now
        ).order_by('-start_date')

    
    # Initialize statistics
    user_attempts_count = 0
    total_attempts_possible = 0
    total_score = 0
    scored_attempts_count = 0
    active_quizzes_count = 0
    
    # Process each quiz
    for quiz in qa_quizzes:
        # Calculate availability
        quiz.is_available = quiz.start_date <= now <= quiz.end_date
        if quiz.is_available:
            active_quizzes_count += 1
        
        if request.user.is_authenticated:
            # Get user attempts for this quiz
            attempts = MCQAttempt.objects.filter(
                quiz=quiz, 
                student=request.user
            )
            quiz.user_attempts = attempts.count()
            quiz.can_attempt = quiz.user_attempts < quiz.max_attempts
            
            # Update statistics
            user_attempts_count += quiz.user_attempts
            total_attempts_possible += quiz.max_attempts
            
            # Calculate scores for this quiz
            for attempt in attempts:
                if attempt.score is not None:
                    total_score += attempt.score
                    scored_attempts_count += 1
        else:
            quiz.user_attempts = 0
            quiz.can_attempt = False
    
    # Calculate participation rate (avoid division by zero)
    participation_rate = 0
    if total_attempts_possible > 0:
        participation_rate = (user_attempts_count / total_attempts_possible) * 100
    
    # Calculate average score (avoid division by zero)
    average_score = 0
    if scored_attempts_count > 0:
        average_score = total_score / scored_attempts_count
    
    # Get total quiz count (for pagination)
    total_quizzes_count = qa_quizzes.count()
    
    # Pagination
    paginator = Paginator(qa_quizzes, 12)
    page_number = request.GET.get('page')
    try:
        qa_quizzes = paginator.page(page_number)
    except PageNotAnInteger:
        qa_quizzes = paginator.page(1)
    except EmptyPage:
        qa_quizzes = paginator.page(paginator.num_pages)
    
    context = {
        'qa_quizzes': qa_quizzes,
        'subject': subject,
        'now': now,
        'user_attempts_count': user_attempts_count,
        'total_attempts_possible': total_attempts_possible,
        'participation_rate': participation_rate,
        'average_score': average_score,
        'active_quizzes_count': active_quizzes_count,
        'total_quizzes_count': total_quizzes_count,
    }
    
    return render(request, 'quizzes/mcqs/list_subject_mcq_quizzes.html', context)


# # RESULTS
@login_required
def mcq_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            # Admin sees only their own results when "My Results" is selected
            mcq_results = MCQResult.objects.filter(student=request.user)
        else:
            # Admin sees all results when "All Results" is selected
            mcq_results = MCQResult.objects.all()
    elif request.user.is_student:
        mcq_results = MCQResult.objects.filter(student=request.user)

    else:
        mcq_results = []
    
    return render(request, 'quizzes/mcqs/mcq_results.html', {
        'mcq_results': mcq_results,
    })


@login_required
def mcq_quiz_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            # Admin sees only their own quiz attempts
            mcq_attempts = MCQAttempt.objects.filter(student=request.user).order_by('-end_time')
        else:
            # Admin sees all quiz attempts
            mcq_attempts = MCQAttempt.objects.all().order_by('-end_time')
    elif request.user.is_student:
        mcq_attempts = MCQAttempt.objects.filter(
            student=request.user
        ).order_by('-end_time')
    else:
        mcq_attempts = []
    
    return render(request, 'quizzes/mcqs/mcq_quiz_results.html', {
        'mcq_attempts': mcq_attempts,
    })


@login_required
def qa_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            qa_results = QAResult.objects.filter(student=request.user).order_by('-created_at')
        else:
            qa_results = QAResult.objects.all().order_by('-created_at')
    elif request.user.is_student:
        qa_results = QAResult.objects.filter(student=request.user)
    else:
        qa_results = []
    
    return render(request, 'quizzes/qas/qa_results.html', {'qa_results': qa_results})


@login_required
def qa_quiz_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            qa_attempts = QAAttempt.objects.filter(student=request.user).order_by('-end_time')
        else:
            qa_attempts = QAAttempt.objects.all().order_by('-end_time')
    elif request.user.is_student:
        qa_attempts = QAAttempt.objects.filter(
            student=request.user
        ).order_by('-end_time')
    else:
        qa_attempts = []
    
    return render(request, 'quizzes/qas/qa_quiz_results.html', {
        'qa_attempts': qa_attempts
    })


@login_required
def tf_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_staff:
        if view_type == 'my':
            tf_results = TrueFalseResult.objects.filter(student=request.user).order_by('-created_at')
        else:
            tf_results = TrueFalseResult.objects.all().order_by('-created_at')
    elif request.user.is_student:
        tf_results = TrueFalseResult.objects.filter(student=request.user)
    else:
        tf_results = []
    
    return render(request, 'quizzes/tfs/tf_results.html', {'tf_results': tf_results})
