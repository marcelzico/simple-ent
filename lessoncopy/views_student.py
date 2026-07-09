"""
Student-facing views for lesson content (copies, resumes, annotations, study tracking)
All views are protected by subscription checks where appropriate.
""" 
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Copy, Resume, UserAnnotation, StudySession, Importer
from .forms import ResumeForm
from lecon.models import Chapter, Unite
from subscriptions.models import Subscription, SubscriptionUsageAudit
from subscriptions.decorators import student_required, active_subscription_required
from .utils import prepare_table_data
from django.db.models import Sum
import json 
from django.views.decorators.csrf import ensure_csrf_cookie

# __________________________________________________________
#           Chapter contents lesson materials
# __________________________________________________________

@student_required
@active_subscription_required()
def chapter_copies_view(request, unite_id, chapter_id):
    """
    Main view to display all lesson content (Copies) for a chapter.
    Basic access requires any active subscription.
    """
    chapter = get_object_or_404(Chapter, ue__id=unite_id, id=chapter_id)
    unite = chapter.ue

    profile = request.user.student_profile
    if unite.level != profile.level:
        messages.error(request, "Ce chapitre n'est pas disponible pour votre niveau d'études.")
        return redirect('lecon:subject_list')

    # Get all importers (upload sessions) for this chapter
    importers = Importer.objects.filter(chapter=chapter).order_by('-uploaded_at')
    
    # Initialize variables
    selected_importer = None
    copies = Copy.objects.none()
    
    # Check if a specific importer was requested
    selected_importer_id = request.GET.get('importer')
    if selected_importer_id:
        try:
            selected_importer = get_object_or_404(Importer, id=selected_importer_id, chapter=chapter)
            copies = Copy.objects.filter(chapter=chapter, importer=selected_importer).order_by('id')
        except:
            selected_importer = None
    
    # If no importer selected or invalid, use the latest
    if not selected_importer and importers.exists():
        selected_importer = importers.first()
        copies = Copy.objects.filter(chapter=chapter, importer=selected_importer).order_by('id')
    else:
        # If no importers exist, just show all copies (for backward compatibility)
        copies = Copy.objects.filter(chapter=chapter).order_by('id')

    # Prepare table data if any Copy has JSON table
    def tableur():
        for copie in copies:
            if copie.table:
                return copie.table
        return None
    
    table_data = prepare_table_data(tableur(), header=True)

    active_sub = Subscription.get_student_active_subscription(profile)

    context = {
        'chapter': chapter,
        'unite': unite,
        'copies': copies,
        "table_data": table_data,
        "importers": importers,
        "selected_importer": selected_importer,
    }

    # Log chapter content view
    SubscriptionUsageAudit.log_usage(
        action_type='feature_access',
        details={
            'feature': 'view_lesson_content',
            'chapter_id': chapter.id,
            'copy_count': copies.count(),
        },
        request=request,
        subscription=active_sub,
        student=profile
    )

    return render(request, 'lessoncopy/lesson_student.html', context)

# _________________________________________
#          Student study session
# _________________________________________

@student_required
@active_subscription_required()
@require_POST
@csrf_exempt
def start_study_session(request):
    """
    AJAX – begin tracking study time for this chapter
    """
    try:
        import json
        data = json.loads(request.body)
        chapter_id = data.get('chapter_id')
        
        if not chapter_id:
            return JsonResponse({'success': False, 'error': 'Chapter ID requis'}, status=400)
            
        chapter = get_object_or_404(Chapter, id=chapter_id)
        
        # Check if there's already an active session
        active_session = StudySession.objects.filter(
            user=request.user,
            chapter=chapter,
            end_time__isnull=True
        ).first()
        
        if active_session:
            # Return existing session ID
            return JsonResponse({
                'success': True,
                'session_id': active_session.id,
                'message': 'Session déjà active'
            })
        
        # Create new session
        session = StudySession.objects.create(
            user=request.user,
            chapter=chapter,
            start_time=timezone.now(),
        )
        
        SubscriptionUsageAudit.log_usage(
            action_type='study_session_start',
            details={
                'chapter_id': chapter.id,
            },
            request=request,
            student=request.user.student_profile
        )
        
        return JsonResponse({
            'success': True,
            'session_id': session.id
        })
        
    except Exception as e:
        print(f"Error starting study session: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@student_required
@active_subscription_required()
@require_POST
@csrf_exempt
def end_study_session(request):
    """
    AJAX – stop study timer and save duration
    """
    try:
        import json
        data = json.loads(request.body)
        session_id = data.get('session_id')
        duration_seconds = data.get('duration_seconds', 0)
        
        if not session_id:
            return JsonResponse({'success': False, 'error': 'Session ID requis'}, status=400)
            
        # Get the session
        session = StudySession.objects.get(id=session_id, user=request.user)
        
        # Only update if not already ended
        if session.end_time is None:
            now = timezone.now()
            session.end_time = now
            session.duration_seconds = duration_seconds
            session.completed = True
            session.save()
        
        SubscriptionUsageAudit.log_usage(
            action_type='study_session_end',
            details={
                'chapter_id': session.chapter.id,
                'duration_seconds': duration_seconds,
            },
            request=request,
            student=request.user.student_profile
        )
        
        return JsonResponse({
            'success': True,
            'duration_seconds': duration_seconds,
            'duration_human': f"{duration_seconds // 60} min {duration_seconds % 60} s"
        })
        
    except StudySession.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Session non trouvée'}, status=404)
    except Exception as e:
        print(f"Error ending study session: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)            

# _________________________________________
#          Student annotations
# _________________________________________

@student_required
@active_subscription_required(feature='can_add_notes')
@require_POST
def add_user_annotation(request, copy_id):
    """
    AJAX or form-based: let student highlight text + add personal note
    """
    copy = get_object_or_404(Copy, id=copy_id)

    # Quick authorization double-check
    if copy.chapter.ue.level != request.user.student_profile.level:
        return JsonResponse({'success': False, 'error': 'Niveau non autorisé'}, status=403)

    highlighted_text = request.POST.get('highlighted_text', '').strip()
    user_note = request.POST.get('user_note', '').strip()
    color = request.POST.get('color', 'yellow')

    if not highlighted_text:
        return JsonResponse({'success': False, 'error': 'Aucun texte surligné'}, status=400)

    annotation, created = UserAnnotation.objects.get_or_create(
        user=request.user,
        copy=copy,
        highlighted_text=highlighted_text,
        defaults={
            'user_note': user_note,
            'color': color,
        }
    )

    if not created:
        # update if already exists (optional – or return error)
        annotation.user_note = user_note
        annotation.color = color
        annotation.save()

    SubscriptionUsageAudit.log_usage(
        action_type='feature_access',
        details={
            'feature': 'can_add_notes',
            'action': 'add_annotation',
            'copy_id': copy.id,
        },
        request=request,
        student=request.user.student_profile
    )

    return JsonResponse({
        'success': True,
        'annotation_id': annotation.id,
        'message': 'Annotation enregistrée'
    })


@ensure_csrf_cookie
@require_POST
def update_annotation(request):
    """Update user annotation"""
    try:
        data = json.loads(request.body)
        annotation_id = data.get('annotation_id')
        user_note = data.get('user_note', '')
        color = data.get('color', 'yellow')
        
        annotation = UserAnnotation.objects.get(id=annotation_id, user=request.user)
        annotation.user_note = user_note
        annotation.color = color
        annotation.save()
        
        return JsonResponse({'status': 'updated'})
        
    except UserAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Annotation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@ensure_csrf_cookie
def get_annotations(request, chapter_id):
    """Get all annotations for a chapter with error handling"""
    try:
        annotations = UserAnnotation.objects.filter(
            user=request.user,
            copy__chapter_id=chapter_id
        ).select_related('copy').order_by('-created_at')
        
        annotations_data = []
        for annotation in annotations:
            annotations_data.append({
                'id': annotation.id,  # Make sure this is included
                'highlighted_text': annotation.highlighted_text,  # Make sure this is included
                'user_note': annotation.user_note,
                'color': annotation.color,
                'created_at': annotation.created_at.isoformat(),
                'copy_id': annotation.copy.id,  # Make sure this is included
                'copy_heading': annotation.copy.heading
            })
        
        print(f"Returning {len(annotations_data)} annotations for chapter {chapter_id}")  # Debug
        return JsonResponse(annotations_data, safe=False)
        
    except Exception as e:
        print(f"Error in get_annotations: {e}")  # Debug
        return JsonResponse({'error': str(e)}, status=400) 


@require_POST
@csrf_exempt
def delete_annotation(request):
    """Delete user annotation"""
    try:
        data = json.loads(request.body)
        annotation_id = data.get('annotation_id')
        
        annotation = UserAnnotation.objects.get(id=annotation_id, user=request.user)
        annotation.delete()
        
        return JsonResponse({'status': 'deleted'})
    except UserAnnotation.DoesNotExist:
        return JsonResponse({'error': 'Annotation not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
    

@student_required
@active_subscription_required()
@require_POST
@csrf_exempt
def save_simple_annotation(request):
    """
    Save simple annotation for a copy (without text selection)
    """
    try:
        # Debug logging
        print(f"save_simple_annotation called by user: {request.user.id}")
        print(f"Request body: {request.body}")
        
        # Parse JSON data
        data = json.loads(request.body)
        copy_id = data.get('copy_id')
        user_note = data.get('user_note', '').strip()
        
        print(f"Copy ID: {copy_id}, User note: {user_note}")
        
        if not copy_id:
            return JsonResponse({
                'success': False, 
                'error': 'ID du contenu requis'
            }, status=400)
        
        try:
            copy = Copy.objects.get(id=copy_id)
        except Copy.DoesNotExist:
            return JsonResponse({
                'success': False, 
                'error': f'Contenu avec ID {copy_id} non trouvé'
            }, status=404)
        
        # Check if annotation already exists for this user and copy
        annotation = UserAnnotation.objects.filter(
            user=request.user,
            copy=copy
        ).first()
        
        if annotation:
            # Update existing annotation
            annotation.user_note = user_note
            annotation.save()
            created = False
            action = 'updated'
        else:
            # Create new annotation
            annotation = UserAnnotation.objects.create(
                user=request.user,
                copy=copy,
                user_note=user_note,
                highlighted_text='',  # Empty for simple annotations
                color='yellow'
            )
            created = True
            action = 'created'
        
        print(f"Annotation {action}: {annotation.id}")
        
        # Try to log usage, but don't fail if it doesn't work
        try:
            SubscriptionUsageAudit.log_usage(
                action_type='feature_access',
                details={
                    'feature': 'can_add_notes',
                    'action': 'save_annotation',
                    'copy_id': copy.id,
                    'annotation_id': annotation.id,
                },
                request=request,
                student=request.user.student_profile
            )
        except Exception as e:
            print(f"Error logging usage: {e}")
            # Don't fail if logging fails
        
        return JsonResponse({
            'success': True,
            'annotation_id': annotation.id,
            'created': created,
            'action': action,
            'message': 'Note sauvegardée avec succès!'
        })
        
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return JsonResponse({
            'success': False, 
            'error': 'Données JSON invalides'
        }, status=400)
    except Exception as e:
        print(f"Unexpected error in save_simple_annotation: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False, 
            'error': f'Erreur interne: {str(e)}'
        }, status=500)
    

@student_required
@active_subscription_required()
@require_POST
@csrf_exempt
def delete_simple_annotation(request):
    """
    Delete annotation for a copy
    """
    try:
        data = json.loads(request.body)
        annotation_id = data.get('annotation_id')
        
        if not annotation_id:
            return JsonResponse({'success': False, 'error': 'ID annotation requis'}, status=400)
        
        annotation = get_object_or_404(UserAnnotation, id=annotation_id, user=request.user)
        copy_id = annotation.copy.id
        annotation.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Note supprimée avec succès!'
        })
        
    except Exception as e:
        print(f"Erreur suppression annotation: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@student_required
@active_subscription_required()
def get_copy_annotation(request, copy_id):
    """
    Get annotation for a specific copy
    """
    try:
        annotation = UserAnnotation.objects.filter(
            user=request.user,
            copy_id=copy_id
        ).first()
        
        if annotation:
            return JsonResponse({
                'has_annotation': True,
                'annotation_id': annotation.id,
                'user_note': annotation.user_note,
                'created_at': annotation.created_at.isoformat(),
                'updated_at': annotation.updated_at.isoformat()
            })
        else:
            return JsonResponse({
                'has_annotation': False
            })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# _________________________________________
#          Student summary
# _________________________________________

@student_required
@active_subscription_required(feature='can_add_resume')
def create_resume(request, chapter_id):
    """
    Student creates a personal resume/summary for the chapter
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    if chapter.ue.level != request.user.student_profile.level:
        messages.error(request, "Niveau non autorisé.")
        return redirect('lecon:chapter_detail', unite_pk=chapter.ue.id, chapter_pk=chapter.id)

    if request.method == 'POST':
        form = ResumeForm(request.POST)
        if form.is_valid():
            resume = form.save(commit=False)
            resume.chapitre = chapter
            resume.createur = request.user
            resume.save()

            messages.success(request, "Votre résumé a été enregistré avec succès.")
            
            SubscriptionUsageAudit.log_usage(
                action_type='feature_access',
                details={
                    'feature': 'can_add_resume',
                    'action': 'create_resume',
                    'chapter_id': chapter.id,
                },
                request=request,
                student=request.user.student_profile
            )

            return redirect('lecon:chapter_detail_student', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    else:
        form = ResumeForm()

    return render(request, 'lessoncopy/resume_form.html', {
        'form': form,
        'chapter': chapter,
        'action': 'create',
    })


@student_required
@active_subscription_required(feature='can_add_resume')
def view_my_resumes(request, chapter_id):
    """
    List personal resumes created by this student for the chapter
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    resumes = Resume.objects.filter(
        chapitre=chapter,
        createur=request.user
    ).order_by('-mis_a_jour')

    context = {
        'chapter': chapter,
        'resumes': resumes,
        'can_edit': True,  # student owns them
    }
    return render(request, 'lessoncopy/student/my_resumes.html', context)


@student_required
@active_subscription_required(feature='can_add_resume')
def edit_resume(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, createur=request.user)

    if request.method == 'POST':
        form = ResumeForm(request.POST, instance=resume)
        if form.is_valid():
            form.save()
            messages.success(request, "Résumé mis à jour.")
            return redirect('lessoncopy:view_my_resumes', chapter_id=resume.chapitre.id)
    else:
        form = ResumeForm(instance=resume)

    return render(request, 'lessoncopy/resume_form.html', {
        'form': form,
        'chapter': resume.chapitre,
        'action': 'edit',
        'resume': resume,
    })


@student_required
@active_subscription_required(feature='can_add_resume')
def delete_resume(request, resume_id):
    resume = get_object_or_404(Resume, id=resume_id, createur=request.user)

    resume.delete()
    return redirect ('lessoncopy:lesson_student', unite_id= resume.chapitre.ue.id, chapter_id= resume.chapitre.id)

# _________________________________________
#          Student statistics
# _________________________________________

@student_required
@active_subscription_required()
def study_stats(request, chapter_id):
    """
    Show personal study time statistics for the chapter
    """
    chapter = get_object_or_404(Chapter, id=chapter_id)

    sessions = StudySession.objects.filter(
        user=request.user,
        chapter=chapter,
        completed=True
    ).order_by('-start_time')

    total_seconds = sessions.aggregate(total=Sum('duration_seconds'))['total'] or 0
    total_hours = total_seconds // 3600
    total_minutes = (total_seconds % 3600) // 60

    context = {
        'chapter': chapter,
        'sessions': sessions[:20],  # last 20 for performance
        'total_hours': total_hours,
        'total_minutes': total_minutes,
        'session_count': sessions.count(),
    }
    return render(request, 'lessoncopy/student/study_stats.html', context)



