from django.views.generic import UpdateView
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render 
from django.urls import reverse
from lecon.models import Chapter, Unite
from .forms import CopyForm, DocumentUploadForm, ResumeIaForm, ResumeForm
from .models import Copy, StudySession, UserAnnotation, ResumeIA, Resume, Importer
from .utils import extract_docx_to_model, prepare_table_data, extract_pptx_to_model, extract_pdf_to_model
from django.contrib import messages
import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
import base64
import PyPDF2
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import io
from subscriptions.decorators import non_student_required, StaffOrSuperuserMixin


@login_required
@non_student_required
def copy_create(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    # Verify ownership
    if not request.user.is_staff:
        raise PermissionDenied

    if request.method == 'POST':
        form = CopyForm(request.POST, request.FILES, chapter=chapter, user=request.user)
        if form.is_valid():
            copy = form.save(commit=False)
            copy.chapter = chapter
            copy.save()
            return redirect('lecon:chapter_detail', unite_pk=chapter.ue.id, chapter_pk=chapter.id)
    else:
        form = CopyForm(chapter=chapter, user=request.user)

    return render(request, 'lessoncopy/copy_form.html', {
        'form': form,
        'chapter': chapter,
    })


@login_required
def copy_view(request, unite_id, chapter_id):
    unite = get_object_or_404(Unite, id=unite_id)
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.user.is_student:
        return redirect('lessoncopy:lesson_student', unite_id=unite.id, chapter_id=chapter.id)

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
            # Fall back to latest if selected importer not found
            selected_importer = None
    
    # If no importer selected or invalid, use the latest
    if not selected_importer and importers.exists():
        selected_importer = importers.first()
        copies = Copy.objects.filter(chapter=chapter, importer=selected_importer).order_by('id')
    else:
        # If no importers exist, just show all copies (for backward compatibility)
        copies = Copy.objects.filter(chapter=chapter).order_by('id')
    
    def tableur():
        for copie in copies:
            if copie.table:
                return copie.table
        return None
    
    table_data = prepare_table_data(tableur(), header=True)

    context = {
        "chapter": chapter,
        "copies": copies,
        "unite": unite,
        "table_data": table_data,
        "importers": importers,
        "selected_importer": selected_importer,
    }

    return render(request, "lessoncopy/lesson.html", context)


@login_required
@non_student_required
def modify_copy(request, chapter_id, copy_id):
    chapter = Chapter.objects.get (id = chapter_id)
    copy = Copy.objects.get (id = copy_id, chapter = chapter_id)
    
    if request.method == 'POST':
        form = CopyForm (request.POST, request.FILES, instance=copy)
        if form.is_valid():
            form.save()
            messages.success (request, 'The modifcations saved succeffuly!')
            return redirect ('lessoncopy:lesson', chapter.ue.id, chapter.id)
    else:
        form = CopyForm (instance = copy)
    
    return render (request, 'lessoncopy/modify_copy_form.html', {'chapter': chapter, 'copy': copy, 'form': form})


@login_required
@non_student_required
def delete_copy(request, chapter_id, copy_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    copy = get_object_or_404(Copy, id=copy_id, chapter_id=chapter_id)
    
    if request.method == 'POST':  # confirm before deleting
        copy.delete()
        messages.success(request, 'The copy was deleted successfully!')
        return redirect('lessoncopy:lesson', chapter.ue.id, chapter.id)


class CopyUpdateView(StaffOrSuperuserMixin, UpdateView):
    model = Copy
    form_class = CopyForm
    template_name = 'lessoncopy/edit.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['chapter'] = self.object.chapter
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        # Get the chapter from the Copy instance
        chapter = self.object.chapter
        
        # Verify the chapter and its related Unite exist
        if not chapter or not chapter.ue:
            raise ValueError("Associated chapter or Unite not found")
        
        return reverse('lecon:chapter_detail', kwargs={
            'subject_pk': chapter.ue.id,
            'chapter_pk': chapter.id
        })
    
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.is_student:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


@login_required
@non_student_required
def create_resume_ia (request, chapter_id):
    chapitre = Chapter.objects.get (id=chapter_id)
   
    if request.method == 'POST':
        form = ResumeIaForm()
        if form.is_valid():
            form.chapitre = chapitre
            form.save()
            messages.success(request, 'Le résumé IA a été créé avec succès!')
            return redirect('lecon:chapter_detail', unite_pk=chapitre.ue.id, chapter_id=chapitre.id)
    
    else:
        form = ResumeForm()

    return render (request, 'lessoncopy/create_ai_resume.html', {'form': form, 'chapitre': chapitre})


@login_required
@non_student_required
def edit_ai_resume(request, resume_id):
    resume = get_object_or_404(ResumeIA, id=resume_id)
    
    if request.method == 'POST':
        resume_text = request.POST.get('resume')
        if resume_text:
            resume.resume = resume_text
            resume.save()
            messages.success(request, 'Le résumé IA a été modifié avec succès!')
            return redirect('lecon:chapter_detail', subject_pk=resume.chapitre.ue.id, chapter_pk=resume.chapitre.id)
        else:
            messages.error(request, 'Le résumé ne peut pas être vide.')
    
    return render(request, 'lessoncopy/edit_ai_resume.html', {'resume': resume})


@login_required
@non_student_required
def delete_ai_resume(request, resume_id):
    resume = get_object_or_404(ResumeIA, id=resume_id)
    chapter = resume.chapitre
    
    if request.method == 'POST':
        resume.delete()
        messages.success(request, 'Le résumé IA a été supprimé avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'lessoncopy/delete_ai_resume.html', {'resume': resume})


@login_required
@non_student_required
def edit_document(request, document_id):
    document = get_object_or_404(Importer, id=document_id)
    
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        document.file_type = file_type
        document.save()
        messages.success(request, 'Document modifié avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=document.chapter.ue.id, chapter_pk=document.chapter.id)
    
    return render(request, 'lessoncopy/edit_document.html', {'document': document})


@login_required
@non_student_required
def delete_document(request, document_id):
    document = get_object_or_404(Importer, id=document_id)
    chapter = document.chapter
    
    if request.method == 'POST':
        document.delete()
        messages.success(request, 'Document supprimé avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'lessoncopy/delete_document.html', {'document': document})


@login_required
@non_student_required
def delete_all_documents(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if not request.user.is_staff:
        raise PermissionDenied
    
    if request.method == 'POST':
        count, _ = Importer.objects.filter(chapter=chapter).delete()
        messages.success(request, f'{count} document(s) supprimé(s) avec succès!')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'lessoncopy/delete_all_documents.html', {'chapter': chapter})


# Content Management Views
@login_required
@non_student_required
def delete_all_content(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    if not request.user.is_staff:
        raise PermissionDenied
    
    if request.method == 'POST':
        copy_count, _ = Copy.objects.filter(chapter=chapter).delete()
        messages.success(request, f'Tout le contenu a été supprimé! ({copy_count} éléments)')
        return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    
    return render(request, 'lessoncopy/delete_all_content.html', {'chapter': chapter})


@login_required
@non_student_required
def upload_document(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.chapter = chapter
            
            file_obj = request.FILES.get('file')
            
            if not file_obj:
                form.add_error('file', 'Aucun fichier téléchargé')
                return render(request, 'lessoncopy/upload_document.html', {'form': form, 'chapter': chapter})
            
            # Determine file type
            filename = file_obj.name
            ext = os.path.splitext(filename)[1].lower()
            
            # Save the file first
            uploaded_file.file.save(filename, file_obj)
            uploaded_file.title = os.path.splitext(filename)[0]
            
            if ext == '.docx':
                uploaded_file.file_type = 'docx'
                uploaded_file.processed = False
                uploaded_file.save()
                
                try:
                    # Extract Word content with proper heading levels
                    extract_docx_to_model(uploaded_file.file.path, chapter_id, uploaded_file)
                    uploaded_file.processed = True
                    uploaded_file.save()
                    messages.success(request, 'Document Word importé avec succès !')
                except Exception as e:
                    messages.warning(request, f'Document enregistré, mais erreur lors de l\'extraction : {str(e)}')
                    
            # elif ext == '.pdf':
            #     uploaded_file.file_type = 'pdf'
            #     uploaded_file.processed = True
            #     uploaded_file.save()
                 
            #     try:
            #         # Extract PDF content
            #         extract_pdf_to_model(uploaded_file.file.path, chapter_id, uploaded_file)
                    
            #         # Get page count
            #         with uploaded_file.file.open('rb') as f:
            #             import PyPDF2
            #             pdf_reader = PyPDF2.PdfReader(f)
            #             uploaded_file.page_count = len(pdf_reader.pages)
            #             uploaded_file.save()
                    
            #         messages.success(request, 'PDF importé avec succès !')
            #     except Exception as e:
            #         messages.warning(request, f'PDF enregistré, mais erreur lors de l\'extraction : {str(e)}')
                
            elif ext == '.pptx':
                uploaded_file.file_type = 'pptx'
                uploaded_file.processed = False
                uploaded_file.save()
                
                try:
                    # Extract PowerPoint content
                    extract_pptx_to_model(uploaded_file.file.path, chapter_id, uploaded_file)
                    uploaded_file.processed = True
                    uploaded_file.save()
                    messages.success(request, 'Présentation PowerPoint importée avec succès !')
                except Exception as e:
                    messages.warning(request, f'Présentation enregistrée, mais erreur lors de l\'extraction : {str(e)}')
                    
            else: 
                form.add_error('file', 'Type de fichier non supporté')
                return render(request, 'lessoncopy/upload_document.html', {'form': form, 'chapter': chapter})
            
            return redirect('lecon:chapter_detail', chapter.ue.id, chapter.id)
    else:
        form = DocumentUploadForm()
    
    return render(request, 'lessoncopy/upload_document.html', {'form': form, 'chapter': chapter})


# Add new view for PDF viewer
@login_required
def view_document(request, document_id):
    """View a document (PDF viewer or normal page)"""
    document = get_object_or_404(Importer, id=document_id)
    
    # Check if user has access to this chapter
    if request.user.is_student:
        # Verify student has access to this chapter's unit
        pass  # Add your access logic here
    
    if document.file_type == 'pdf':
        # Show PDF viewer
        return render(request, 'lessoncopy/pdf_viewer.html', {
            'document': document,
        })
    else:
        # For other file types, redirect to chapter page
        messages.info(request, f'Ce document ({document.get_file_type_display()}) est intégré au chapitre.')
        return redirect('lecon:chapter_detail', 
                       subject_pk=document.chapter.ue.id, 
                       chapter_pk=document.chapter.id)


@login_required
def get_pdf_data(request, document_id):
    """Return PDF as base64 for PDF.js viewer"""
    document = get_object_or_404(Importer, id=document_id, file_type='pdf')
    
    try:
        # Check if file exists
        if not document.file:
            return JsonResponse({
                'success': False,
                'error': 'PDF file not found'
            }, status=404)
        
        # Read and encode PDF
        with open(document.file.path, 'rb') as f:
            pdf_data = base64.b64encode(f.read()).decode('utf-8')
        
        return JsonResponse({
            'success': True,
            'title': document.title or document.file.name,
            'page_count': document.page_count or 0,
            'data': pdf_data
        })
    except FileNotFoundError:
        return JsonResponse({
            'success': False,
            'error': 'PDF file not found on server'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@login_required
def search_pdf(request, document_id):
    """Search text in PDF"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    document = get_object_or_404(Importer, id=document_id, file_type='pdf')
    
    try:
        data = json.loads(request.body)
        search_term = data.get('search_term', '').strip().lower()
        
        if not search_term:
            return JsonResponse({'matches': []})
        
        matches = []
        
        # Check if file exists
        if not os.path.exists(document.file.path):
            return JsonResponse({'error': 'PDF file not found'}, status=404)
        
        with open(document.file.path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text().lower()
                
                if search_term in text:
                    # Count occurrences
                    count = text.count(search_term)
                    
                    # Get context
                    start_index = text.find(search_term)
                    context_start = max(0, start_index - 50)
                    context_end = min(len(text), start_index + len(search_term) + 50)
                    context = text[context_start:context_end]
                    
                    if context_start > 0:
                        context = '...' + context
                    if context_end < len(text):
                        context = context + '...'
                    
                    matches.append({
                        'page': page_num + 1,
                        'context': context,
                        'count': count
                    })
        
        return JsonResponse({'matches': matches})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


