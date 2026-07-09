from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from .models import MCQQuiz, MCQAttempt, MCQ, MCQResult
from .forms import MCQForm, MCQQuizForm, CSVUploadForm
from lecon.models import Chapter, Unite
from utilisateur.models import User
from django.contrib import messages
import csv
from io import TextIOWrapper
from django.views.decorators.csrf import csrf_exempt
from django.db import models
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from . decorators import staff_required
from student.models import StudentProfile
from subscriptions.decorators import non_student_required
from django.core.exceptions import PermissionDenied
from subscriptions.models import Subscription
from datetime import date


# CREATE
@login_required
@non_student_required
def create_mcq(request, chapter_pk):
    chapter = get_object_or_404(Chapter, pk=chapter_pk)
    
    if request.method == 'POST':
        form = MCQForm(request.POST)
        if form.is_valid():
            mcq = form.save(commit=False)
            mcq.chapter = chapter
            mcq.created_by = request.user
            mcq.save()
            messages.success(request, 'MCQ added successfully!')
            return redirect('quizzes:view_mcqs', chapter_id=chapter.pk)
    else:
        form = MCQForm()
    
    return render(request, 'quizzes/mcqs/mcq_form.html', {
        'form': form,
        'chapter': chapter,
        'is_superuser': request.user.is_superuser
    })


@login_required
@non_student_required
def create_mcq_quiz(request, subject_pk):
    """Create MCQ Quiz - Subject is REQUIRED"""
    # Get the subject with proper permissions
    subject = get_object_or_404(Unite, id = subject_pk)
    
    
    if request.method == 'POST':
        form = MCQQuizForm(request.POST, subject=subject)
        
        # DEBUG: Print form data
        print("POST data:", request.POST)
        print("Questions from POST:", request.POST.getlist('questions'))
        
        if form.is_valid():
            quiz = form.save(commit=False)
            quiz.subject = subject
            
            try:
                quiz.save()
                form.save_m2m()
                messages.success(request, 'MCQ Quiz created successfully!')
                return redirect('lecon:subject_detail', pk=subject.pk)
            except Exception as e:
                messages.error(request, f'Error creating quiz: {str(e)}')
                print(f"Error saving quiz: {e}")
        else:
            # DEBUG: Show form errors
            print("Form errors:", form.errors.as_json())
            for field, errors in form.errors.items():
                print(f"Field {field} errors: {errors}")
            messages.error(request, 'Please correct the errors below.')
    else: 
        form = MCQQuizForm(subject=subject)
        # Pre-filter chapters for this subject
        form.fields['chapters'].queryset = subject.chapters.all()
        # DEBUG: Show initial queryset
        print("Initial questions queryset count:", form.fields['questions'].queryset.count())
    
    return render(request, 'quizzes/mcqs/mcq_quiz_form.html', {
        'form': form,
        'subject': subject
    })


# Quiz Listing Views
@login_required
def list_mcq_quizzes(request, subject_pk=None):
    """List all MCQ quizzes for a subject or all subjects"""
    now = timezone.now()
    
    if subject_pk:
        subject = get_object_or_404(Unite, pk=subject_pk)
        if request.user.is_student:
            mcq_quizzes = MCQQuiz.objects.filter(
                subject=subject,
                end_date__gte=now
            ).order_by('-start_date')
        else:
            mcq_quizzes = MCQQuiz.objects.filter(
                subject=subject
            ).order_by('-created_at')
    else:
        if request.user.is_student:
            mcq_quizzes = MCQQuiz.objects.filter(
                end_date__gte=now
            ).order_by('-start_date')
        else:
            mcq_quizzes = MCQQuiz.objects.all().order_by('-created_at')
    
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
        'subject': subject if subject_pk else None,
        'now': now,
        'user_attempts_count': user_attempts_count,
        'total_attempts_possible': total_attempts_possible,
        'participation_rate': participation_rate,
        'average_score': average_score,
        'active_quizzes_count': active_quizzes_count,
        'total_quizzes_count': total_quizzes_count,
    }
    
    return render(request, 'quizzes/mcqs/list_mcq_quizzes.html', context)


# With class and enrollement status distinction
@login_required
def list_subject_mcq_quizzes(request, subject_pk):
    """List all MCQ quizzes for a subject or all subjects"""
    now = timezone.now()
    
    subject = Unite.objects.filter(id=subject_pk).first()
    mcq_quizzes = MCQQuiz.objects.filter(subject=subject).order_by('-created_at')

    if request.user.is_student:
        today = date.today()
        active_subscription = Subscription.objects.filter(
            student=request.user.student_profile,
            payement_status='approved',
            start_date__lte=today,
            expires_at__gte=today
        ).first()
        if active_subscription:
            subject = Unite.objects.filter(id=subject_pk,
                level=request.user.student_profile.level,
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


# Quiz Detail Views
@login_required
@non_student_required
def mcq_quiz_detail(request, quiz_id):
    """View quiz details before attempting"""
    quiz = get_object_or_404(MCQQuiz, pk=quiz_id)
    now = timezone.now()
    
    # Check permissions
    if request.user.is_student and (now < quiz.start_date or now > quiz.end_date):
        messages.error(request, "This quiz is not currently available.")
        return redirect('quizzes:list_mcq_quizzes')
    
    # Get user attempts
    attempts = MCQAttempt.objects.filter(
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
    
    return render(request, 'quizzes/mcqs/mcq_quiz_detail.html', context)


@login_required
@non_student_required
def edit_mcq_quiz(request, quiz_id):
    """Edit an existing MCQ quiz"""
    quiz = get_object_or_404(MCQQuiz, pk=quiz_id)
    subject = quiz.subject
    
    # Permission check

    
    
    if request.method == 'POST':
        form = MCQQuizForm(request.POST, instance=quiz, student=request.user, subject=subject)
        if form.is_valid():
            form.save()
            messages.success(request, 'Quiz updated successfully!')
            return redirect('quizzes:mcq_quiz_detail', quiz_id=quiz_id)
    else:
        form = MCQQuizForm(instance=quiz, student=request.user, subject=subject)
    
    return render(request, 'quizzes/mcqs/edit_qcm_quiz.html', {
        'form': form,
        'subject': subject,
        'quiz': quiz,
        'is_edit': True,
    })


@login_required
@non_student_required
def delete_mcq_quiz(request, quiz_id):
    """Delete an MCQ quiz"""
    quiz = get_object_or_404(MCQQuiz, pk=quiz_id)
    subject = quiz.subject
    
    # Permission check
    
    
    if request.method == 'POST':
        # Check confirmation
        confirmation = request.POST.get('confirmation', '').strip()
        if confirmation.upper() != 'DELETE':
            messages.error(request, "Please type 'DELETE' to confirm deletion.")
            return render(request, 'quizzes/mcqs/delete_mcq_quiz.html', {
                'quiz': quiz,
                'subject': subject,
            })
        
        # Get attempt count before deletion for message
        attempt_count = quiz.attempts.count()
        quiz_title = quiz.title
        
        # Delete the quiz
        quiz.delete()
        
        messages.success(request, f'Quiz "{quiz_title}" has been permanently deleted.')
        if attempt_count > 0:
            messages.info(request, f'{attempt_count} student attempt(s) were also deleted.')
        
        return redirect('quizzes:list_subject_mcq_quizzes', subject_pk=subject.pk)
    
    return render(request, 'quizzes/mcqs/delete_mcq_quiz.html', {
        'quiz': quiz,
        'subject': subject,
    })


@csrf_exempt
def load_questions_ajax(request):
    """AJAX view to load MCQ questions for selected chapters"""
    try:
        chapter_ids = request.GET.get('chapter_ids', '')
        
        if chapter_ids:
            chapter_id_list = [int(id.strip()) for id in chapter_ids.split(',') if id.strip()]
            
            # Get questions for these chapters
            questions = MCQ.objects.filter(chapter_id__in=chapter_id_list)
            
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
        print(f"Error in MCQ AJAX view: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

 
@login_required
@non_student_required
def upload_csv_mcq(request, chapter_id):
    chapter = Chapter.objects.get(id = chapter_id)
    user = request.user
    
    if user.is_student:
        raise PermissionDenied
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('quizzes:upload_csv_mcq', chapter_id)
            
            try:
                file_data = TextIOWrapper(csv_file.file, encoding='utf-8')
                csv_reader = csv.DictReader(file_data)
                
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        MCQ.objects.create(
                            chapter = chapter,
                            created_by = user,
                            question = row.get('question'),
                            option1 = row.get('option1'),
                            option2 = row.get('option2'),
                            option3 = row.get('option3'),
                            option4 = row.get('option4'),
                            correct_option = row.get('answer') or row.get('réponse') or row.get('correct') or row.get('correcte') or row.get('reponse'),
                            explanation = row.get('explanation') or row.get('explication'),
                            time_limit = 30,
                        )
                    except Exception as e:
                        messages.warning(request, f'Error in row {row_num}: {str(e)}')
                        continue
                
                messages.success(request, 'CSV data imported successfully!')
                return redirect('quizzes:view_mcqs', chapter_id=chapter.id)
            
            except Exception as e:
                messages.error(request, f'Error processing CSV: {str(e)}')
                return redirect('quizzes:upload_csv_mcq', chapter_id)
    else:
        form = CSVUploadForm()
    
    return render(request, 'quizzes/mcqs/upload_csv_mcq.html', {'form': form, 'chapter': chapter})


@non_student_required
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
    else:
        # Students see only their own attempts
        mcq_attempts = MCQAttempt.objects.filter(
            student=request.user
        ).order_by('-end_time')
    
    return render(request, 'quizzes/mcqs/mcq_quiz_results.html', {
        'mcq_attempts': mcq_attempts,
    })


# Delete Views
@login_required
@staff_required
def delete_all_mcqs(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        count, _ = MCQ.objects.filter(chapter=chapter).delete()
        messages.success(request, f'{count} QCM(s) supprimé(s) avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'quizzes/mcqs/delete_all_mcqs.html', {'chapter': chapter})


# MCQ - Delete
@login_required
def delete_mcq(request, mcq_id):
    mcq = get_object_or_404(MCQ, pk=mcq_id)
    chapter = mcq.chapter
    
    if request.method == 'POST':
        mcq.delete()
        messages.success(request, 'MCQ deleted successfully!')
        return redirect('quizzes:view_mcqs', chapter_id=chapter.id)
    
    # For GET requests (modal), we don't need to render a separate page
    # The modal will handle the confirmation
    return redirect('quizzes:view_mcqs', chapter_id=chapter.id)


# MCQ - Bulk Actions
@login_required
@non_student_required
def mcq_bulk_actions(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_mcqs = request.POST.getlist('selected_mcqs')
        
        if not selected_mcqs:
            messages.error(request, 'No MCQs selected.')
            return redirect('quizzes:view_mcqs', chapter_id=chapter.id)
        
        if action == 'delete':
            count, _ = MCQ.objects.filter(id__in=selected_mcqs).delete()
            messages.success(request, f'{count} MCQ(s) deleted successfully!')
        elif action == 'update_time_limit':
            time_limit = request.POST.get('time_limit', 60)
            try:
                time_limit = int(time_limit)
                MCQ.objects.filter(id__in=selected_mcqs).update(time_limit=time_limit)
                messages.success(request, f'Time limit updated for {len(selected_mcqs)} MCQ(s)!')
            except ValueError:
                messages.error(request, 'Invalid time limit value.')
        
        return redirect('quizzes:view_mcqs', chapter_id=chapter.id)
    
    return redirect('quizzes:view_mcqs', chapter_id=chapter.id)


# MCQ - Update (Fixed for explanation)
@login_required
@non_student_required
def update_mcq(request, mcq_id):
    mcq = get_object_or_404(MCQ, pk=mcq_id)
    chapter = mcq.chapter
    
    if request.method == 'POST':
        form = MCQForm(request.POST, instance=mcq)
        if form.is_valid():
            mcq = form.save(commit=False)
            # Ensure explanation is saved (it's already in the form, but let's be explicit)
            mcq.explanation = form.cleaned_data.get('explanation', '')
            mcq.save()
            messages.success(request, 'MCQ updated successfully!')
            return redirect('quizzes:view_mcqs', chapter_id=chapter.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MCQForm(instance=mcq)
    
    return render(request, 'quizzes/mcqs/mcq_form.html', {
        'form': form,
        'chapter': chapter,
        'mcq': mcq,
        'is_update': True,
        'is_superuser': request.user.is_superuser
    })


@login_required
@non_student_required
def view_mcqs(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    mcqs_list = MCQ.objects.filter(chapter=chapter).order_by('-created_at')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        mcqs_list = mcqs_list.filter(
            models.Q(question__icontains=search_query) |
            models.Q(option1__icontains=search_query) |
            models.Q(option2__icontains=search_query) |
            models.Q(option3__icontains=search_query) |
            models.Q(option4__icontains=search_query) |
            models.Q(explanation__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(mcqs_list, 10)
    page_number = request.GET.get('page')
    mcqs = paginator.get_page(page_number)
    
    # Pass search query back to template
    context = {
        'chapter': chapter,
        'mcqs': mcqs,
        'search_query': search_query,
        'result_count': mcqs_list.count(),
    }
    
    return render(request, 'quizzes/mcqs/view_mcqs.html', context)


