from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from .models import QAQuiz, QAAttempt, StudentAnswer, QuestionAnswer, QAAnswer, QAResult, TrueFalseQuiz, TrueFalseResult
from .forms import QAForm, QAQuizForm, CSVUploadForm
from lecon.models import Chapter, Unite
from utilisateur.models import User
from django.contrib import messages
import csv
from io import TextIOWrapper
from django.views.decorators.csrf import csrf_exempt
from .utils import similarity_analyzer
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .decorators import staff_required
from subscriptions.decorators import non_student_required
from django.core.exceptions import PermissionDenied


@login_required
@non_student_required
def create_qa(request, chapter_pk):
    chapter = get_object_or_404(Chapter, pk=chapter_pk)
    
    if request.method == 'POST':
        form = QAForm(request.POST)
        if form.is_valid():
            qa = form.save(commit=False)
            qa.chapter = chapter
            qa.created_by = request.user
            qa.save()
            messages.success(request, 'Question & Answer added successfully!')
            return redirect('quizzes:view_qas', chapter_id=chapter.pk)
    else:
        form = QAForm()
    
    return render(request, 'quizzes/qas/qa_form.html', {
        'form': form,
        'chapter': chapter,
        'is_superuser': request.user.is_superuser
    })


@login_required
@non_student_required
def create_qa_quiz(request, subject_pk):
    """Create QA Quiz - Subject is REQUIRED"""
    # Get the subject with proper permissions
    subject = get_object_or_404(Unite, id=subject_pk)

    if request.method == 'POST':
        form = QAQuizForm(request.POST, user=request.user, subject=subject)
        
        # DEBUG
        print("QA Quiz - POST data received")
        print("Question IDs from POST:", request.POST.getlist('questions'))
        
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = subject
            
            try:
                quiz.save()
                # Save many-to-many relationships
                form.save_m2m()
                messages.success(request, 'QA Quiz created successfully!')
                return redirect('lecon:subject_detail', pk=subject.pk)
            except Exception as e:
                messages.error(request, f'Error creating quiz: {str(e)}')
                print(f"Error saving QA quiz: {e}")
        else:
            # DEBUG: Show form errors
            for field, errors in form.errors.items():
                print(f"Field {field} errors: {errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = QAQuizForm(user=request.user, subject=subject)
        # Pre-filter chapters for this subject
        form.fields['chapters'].queryset = subject.chapters.all()
    
    return render(request, 'quizzes/qas/qa_quiz_form.html', {
        'form': form,
        'subject': subject
    })


@login_required
def list_qa_quizzes(request, subject_pk=None):
    """List all QA quizzes for a subject or all subjects"""
    now = timezone.now()
    
    if subject_pk:
        subject = get_object_or_404(Unite, pk=subject_pk)
        if request.user.is_student:
            qa_quizzes = QAQuiz.objects.filter(
                subject=subject,
                end_date__gte=now
            ).order_by('-start_date')
        else:
            qa_quizzes = QAQuiz.objects.filter(
                subject=subject
            ).order_by('-created_at')
    else:
        if request.user.is_student:
            qa_quizzes = QAQuiz.objects.filter(
                end_date__gte=now
            ).order_by('-start_date')
        else:
            qa_quizzes = QAQuiz.objects.all().order_by('-created_at')
    
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
            attempts = QAAttempt.objects.filter(
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
        'subject': subject if subject_pk else None,
        'now': now,
        'user_attempts_count': user_attempts_count,
        'total_attempts_possible': total_attempts_possible,
        'participation_rate': participation_rate,
        'average_score': average_score,
        'active_quizzes_count': active_quizzes_count,
        'total_quizzes_count': total_quizzes_count,
    }
    
    return render(request, 'quizzes/qas/list_qa_quizzes.html', context)


@login_required
@non_student_required
def qa_quiz_detail(request, quiz_id):
    """View QA quiz details before attempting"""
    quiz = get_object_or_404(QAQuiz, pk=quiz_id)
    now = timezone.now()

    
    attempts = QAAttempt.objects.filter(
        quiz=quiz, 
        student=request.user
    ).order_by('-end_time')
    
    context = {
        'quiz': quiz,
        'attempts': attempts,
        'now': now,
        'can_attempt': attempts.count() < quiz.max_attempts,
        'is_available': quiz.start_date <= now <= quiz.end_date,
    }
    
    return render(request, 'quizzes/qas/qa_quiz_detail.html', context)


@login_required
@non_student_required
def delete_qa_quiz(request, quiz_id):
    """Delete a QA quiz"""
    quiz = get_object_or_404(QAQuiz, pk=quiz_id)
    subject = quiz.subject 
        
    if request.method == 'POST':
        # Check confirmation
        confirmation = request.POST.get('confirmation', '').strip()
        if confirmation.upper() != 'DELETE':
            messages.error(request, "Please type 'DELETE' to confirm deletion.")
            return render(request, 'quizzes/qas/delete_qa_quiz.html', {
                'quiz': quiz,
                'subject': subject,
            })
        
        # Get attempt count before deletion for message
        attempt_count = quiz.attempts.count()
        quiz_title = quiz.title
        
        # Delete the quiz
        quiz.delete()
        
        messages.success(request, f'QA Quiz "{quiz_title}" has been permanently deleted.')
        if attempt_count > 0:
            messages.info(request, f'{attempt_count} student attempt(s) were also deleted.')
        
        return redirect('quizzes:list_qa_quizzes', subject_pk=subject.pk)
    
    return render(request, 'quizzes/qas/delete_qa_quiz.html', {
        'quiz': quiz,
        'subject': subject,
    })


# Similar views for QA Quiz
@login_required
@non_student_required
def edit_qa_quiz(request, quiz_id):
    quiz = get_object_or_404(QAQuiz, pk=quiz_id)
    subject = quiz.subject

    
    if request.method == 'POST':
        form = QAQuizForm(request.POST, instance=quiz, user=request.user)
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = subject  # Ensure subject stays the same
            quiz.save()
            form.save_m2m()
            messages.success(request, 'QA Quiz updated successfully!')
            return redirect('quizzes:qa_quiz_detail', quiz_id=quiz_id)
    else:
        form = QAQuizForm(instance=quiz, user=request.user)
    
    return render(request, 'quizzes/qas/edit_qa_quiz.html', {
        'form': form,
        'subject': subject,
        'quiz': quiz,
        'is_edit': True,
    })


def load_qa_questions_ajax(request):
    """AJAX view to load QA questions for selected chapters"""
    try:
        chapter_ids = request.GET.get('chapter_ids', '')
        
        if chapter_ids:
            chapter_id_list = [int(id.strip()) for id in chapter_ids.split(',') if id.strip()]
            
            # Get QA questions for these chapters
            questions = QuestionAnswer.objects.filter(chapter_id__in=chapter_id_list)
            
            # Return as list of dictionaries with proper structure
            questions_list = []
            for q in questions:
                questions_list.append({
                    'id': q.id,
                    'question': q.question,
                    'chapter': q.chapter.title,
                })
            
            return JsonResponse({
                'success': True,
                'questions': questions_list,
                'count': len(questions_list)
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No chapters selected'
            })
            
    except Exception as e:
        print(f"QA AJAX - Error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@non_student_required
def upload_csv_qa(request, chapter_id):
    chapter = Chapter.objects.get(id = chapter_id)
    user = request.user

    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('quizzes:upload_csv_qa', chapter_id)
            
            try:
                file_data = TextIOWrapper(csv_file.file, encoding='utf-8')
                csv_reader = csv.DictReader(file_data)
                
                
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        QuestionAnswer.objects.create(
                            chapter = chapter,
                            created_by = user,
                            question = row.get('question'),
                            sample_answer = row.get('answer') or row.get('réponse') or row.get('correct') or row.get('correcte') or row.get('reponse'),
                            explanation = row.get('explanation') or row.get('explication'),
                            time_limit = 30,
                        )
                    except Exception as e:
                        messages.warning(request, f'Error in row {row_num}: {str(e)}')
                        continue
                
                messages.success(request, 'CSV data imported successfully!')
                return redirect('quizzes:view_qas', chapter_id=chapter.id)
            
            except Exception as e:
                messages.error(request, f'Error processing CSV: {str(e)}')
                return redirect('quizzes:upload_csv_qa', chapter_id)
    else:
        form = CSVUploadForm()
    
    return render(request, 'quizzes/qas/upload_csv_qa.html', {'form': form, 'chapter': chapter})


@non_student_required
@login_required
def qa_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            qa_results = QAResult.objects.filter(student=request.user).order_by('-created_at')
        else:
            qa_results = QAResult.objects.all().order_by('-created_at')

    else:
        qa_results = QAResult.objects.filter(student=request.user)
    
    return render(request, 'quizzes/qas/qa_results.html', {'qa_results': qa_results})


@non_student_required
@login_required
def qa_quiz_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            qa_attempts = QAAttempt.objects.filter(student=request.user).order_by('-end_time')
        else:
            qa_attempts = QAAttempt.objects.all().order_by('-end_time')
 
    else:
        qa_attempts = QAAttempt.objects.filter(
            student=request.user
        ).order_by('-end_time')
    
    return render(request, 'quizzes/qas/qa_quiz_results.html', {
        'qa_attempts': qa_attempts
    })


@login_required
@staff_required
def delete_all_qas(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        count, _ = QuestionAnswer.objects.filter(chapter=chapter).delete()
        messages.success(request, f'{count} Q&R(s) supprimé(s) avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'quizzes/qas/delete_all_qas.html', {'chapter': chapter})


# QA - Delete
@login_required
@non_student_required
def delete_qa(request, qa_id):
    qa = get_object_or_404(QuestionAnswer, pk=qa_id)
    chapter = qa.chapter
    
    # Permission chec
    
    if request.method == 'POST':
        qa.delete()
        messages.success(request, 'Q&A deleted successfully!')
        return redirect('quizzes:view_qas', chapter_id=chapter.id)
    
    return redirect('quizzes:view_qas', chapter_id=chapter.id)


# QA - Bulk Actions
@login_required
@non_student_required
def qa_bulk_actions(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    # Permission chec
    
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_qas = request.POST.getlist('selected_qas')
        
        if not selected_qas:
            messages.error(request, 'No Q&As selected.')
            return redirect('quizzes:view_qas', chapter_id=chapter.id)
        
        if action == 'delete':
            count, _ = QuestionAnswer.objects.filter(id__in=selected_qas).delete()
            messages.success(request, f'{count} Q&A(s) deleted successfully!')
        elif action == 'update_time_limit':
            time_limit = request.POST.get('time_limit', 300)
            try:
                time_limit = int(time_limit)
                QuestionAnswer.objects.filter(id__in=selected_qas).update(time_limit=time_limit)
                messages.success(request, f'Time limit updated for {len(selected_qas)} Q&A(s)!')
            except ValueError:
                messages.error(request, 'Invalid time limit value.')
        
        return redirect('quizzes:view_qas', chapter_id=chapter.id)
    
    return redirect('quizzes:view_qas', chapter_id=chapter.id)


# QA - Update (Fixed for explanation and sample_answer)
@login_required
@non_student_required
def update_qa(request, qa_id):
    qa = get_object_or_404(QuestionAnswer, pk=qa_id)
    chapter = qa.chapter
    
    # Permission chec
    
    if request.method == 'POST':
        form = QAForm(request.POST, instance=qa)
        if form.is_valid():
            qa = form.save(commit=False)
            # Save explanation field
            qa.explanation = form.cleaned_data.get('explanation', '')
            # Note: sample_answer is already in QAForm, but let's ensure it's saved
            qa.sample_answer = form.cleaned_data.get('sample_answer', '')
            qa.save()
            messages.success(request, 'Q&A updated successfully!')
            return redirect('quizzes:view_qas', chapter_id=chapter.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Initialize form with existing data
        form = QAForm(instance=qa)
    
    return render(request, 'quizzes/qas/qa_form.html', {
        'form': form,
        'chapter': chapter,
        'qa': qa,
        'is_update': True,
        'is_superuser': request.user.is_superuser
    })


@login_required
@non_student_required
def view_qas(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    qas_list = QuestionAnswer.objects.filter(chapter=chapter).order_by('-created_at')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        qas_list = qas_list.filter(
            models.Q(question__icontains=search_query) |
            models.Q(sample_answer__icontains=search_query) |
            models.Q(explanation__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(qas_list, 10)
    page_number = request.GET.get('page')
    qas = paginator.get_page(page_number)
    
    context = {
        'chapter': chapter,
        'qas': qas,
        'search_query': search_query,
        'result_count': qas_list.count(),
    }
    
    return render(request, 'quizzes/qas/view_qas.html', context)

