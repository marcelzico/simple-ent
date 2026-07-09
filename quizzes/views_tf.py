from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import TrueFalseQuiz, TrueFalseResult
from .forms import CSVUploadForm, TrueFalseForm
from lecon.models import Chapter
from utilisateur.models import User
from django.contrib import messages
import csv
from io import TextIOWrapper
from django.core.serializers import serialize
from django.db import models
from django.core.paginator import Paginator
from . decorators import staff_required
from subscriptions.decorators import  non_student_required
from django.core.exceptions import PermissionDenied


# TRUE OR FALSE 
@login_required
@non_student_required
def upload_csv_tf (request, chapter_id):
    chapter = get_object_or_404 (Chapter, id=chapter_id)
    user = request.user 

    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('quizzes:upload_csv_tf', chapter_id)
            
            try:
                file_data = TextIOWrapper(csv_file.file, encoding='utf-8')
                csv_reader = csv.DictReader(file_data)
                 
                for row_num, row in enumerate(csv_reader, 1):
                    try:
                        TrueFalseQuiz.objects.create(
                            chapter = chapter,
                            created_by = user,
                            question = row.get('question'),
                            answer = row.get('answer') or row.get('réponse') or row.get('correct') or row.get('correcte') or row.get('reponse'),
                            explanation = row.get('explanation') or row.get('explication'),
                            time_limit = 30,
                        )
                    except Exception as e:
                        messages.warning(request, f'Error in row {row_num}: {str(e)}')
                        continue
                
                messages.success(request, 'CSV data imported successfully!')
                return redirect('quizzes:view_tfs', chapter_id=chapter.id)
            
            except Exception as e:
                messages.error(request, f'Error processing CSV: {str(e)}')
                return redirect('quizzes:upload_csv_tf', chapter_id)
    else:
        form = CSVUploadForm()
    
    return render(request, 'quizzes/tfs/upload_csv_tf.html', {'form': form, 'chapter': chapter})


@non_student_required
@login_required
def tf_results(request):
    view_type = request.GET.get('view', 'my')
    
    if request.user.is_superuser:
        if view_type == 'my':
            tf_results = TrueFalseResult.objects.filter(student=request.user).order_by('-created_at')
        else:
            tf_results = TrueFalseResult.objects.all().order_by('-created_at')
   
    else:
        tf_results = TrueFalseResult.objects.filter(student=request.user)
    
    return render(request, 'quizzes/tfs/tf_results.html', {'tf_results': tf_results})


@login_required
@staff_required
def delete_all_tfs(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        count, _ = TrueFalseQuiz.objects.filter(chapter=chapter).delete()
        messages.success(request, f'{count} Vrai/Faux supprimé(s) avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'quizzes/tfs/delete_all_tfs.html', {'chapter': chapter})


# TrueFalse - Delete
@login_required
@non_student_required
def delete_tf(request, tf_id):
    tf = get_object_or_404(TrueFalseQuiz, pk=tf_id)
    chapter = tf.chapter
    
    # Permission check
    
    
    if request.method == 'POST':
        tf.delete()
        messages.success(request, 'True/False question deleted successfully!')
        return redirect('quizzes:view_tfs', chapter_id=chapter.id)
    
    return redirect('quizzes:view_tfs', chapter_id=chapter.id)


# TrueFalse - Bulk Actions
@login_required
@non_student_required
def tf_bulk_actions(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_tfs = request.POST.getlist('selected_tfs')
        
        if not selected_tfs:
            messages.error(request, 'No True/False questions selected.')
            return redirect('quizzes:view_tfs', chapter_id=chapter.id)
        
        if action == 'delete':
            count, _ = TrueFalseQuiz.objects.filter(id__in=selected_tfs).delete()
            messages.success(request, f'{count} True/False question(s) deleted successfully!')
        elif action == 'update_time_limit':
            time_limit = request.POST.get('time_limit', 30)
            try:
                time_limit = int(time_limit)
                TrueFalseQuiz.objects.filter(id__in=selected_tfs).update(time_limit=time_limit)
                messages.success(request, f'Time limit updated for {len(selected_tfs)} True/False question(s)!')
            except ValueError:
                messages.error(request, 'Invalid time limit value.')
        
        return redirect('quizzes:view_tfs', chapter_id=chapter.id)
    
    return redirect('quizzes:view_tfs', chapter_id=chapter.id)


# TrueFalse - Update (Fixed for explanation)
@login_required
@non_student_required
def update_tf(request, tf_id):
    tf = get_object_or_404(TrueFalseQuiz, pk=tf_id)
    chapter = tf.chapter
    
    if request.method == 'POST':
        form = TrueFalseForm(request.POST, instance=tf)
        if form.is_valid():
            tf = form.save(commit=False)
            # Save explanation field
            tf.explanation = form.cleaned_data.get('explanation', '')
            tf.save()
            messages.success(request, 'True/False question updated successfully!')
            return redirect('quizzes:view_tfs', chapter_id=chapter.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TrueFalseForm(instance=tf)
    
    return render(request, 'quizzes/tfs/tf_form.html', {
        'form': form,
        'chapter': chapter,
        'tf': tf,
        'is_update': True,
        'is_superuser': request.user.is_superuser
    })


@login_required
@non_student_required
def view_tfs(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    tfs_list = TrueFalseQuiz.objects.filter(chapter=chapter).order_by('-created_at')
    
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        tfs_list = tfs_list.filter(
            models.Q(question__icontains=search_query) |
            models.Q(explanation__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(tfs_list, 10)
    page_number = request.GET.get('page')
    tfs = paginator.get_page(page_number)
    
    context = {
        'chapter': chapter,
        'tfs': tfs,
        'search_query': search_query,
        'result_count': tfs_list.count(),
    }
    
    return render(request, 'quizzes/tfs/view_tfs.html', context)
