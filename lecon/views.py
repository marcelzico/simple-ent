from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Unite, Chapter,UniteSection
from .forms import  ChapterForm, SubjectForm, UniteSectionForm, ChapterSearchForm, ContentFilterForm, HeadingFilterForm
from django.contrib import messages
from quizzes.models import MCQ, MCQResult, QAResult, QuestionAnswer, TrueFalseQuiz, TrueFalseResult
from lessoncopy.models import StudySession, Resume, ResumeIA, Copy, Importer
# from quizlet_copy.models import FlashcardSet, Flashcard, UserProgress
from django.db.models import Avg, Sum, Q, Prefetch
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from utilisateur.decorators import non_student_required
from utilisateur.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging
import datetime
from django.http import HttpResponse
from django.template.loader import get_template
from io import BytesIO
logger = logging.getLogger(__name__)


@login_required
def subject_list(request):
    
    if request.user.is_staff : 
        context = {
            'profile': request.user,
            'paces': Unite.objects.filter(level__icontains='paces'),
            'deuxieme': Unite.objects.filter(level__icontains='2ème'),
            'troisieme': Unite.objects.filter(level__icontains='3ème'),
            'quatrieme': Unite.objects.filter(level__icontains='4ème'),
            'cinquieme': Unite.objects.filter(level__icontains='5ème'),
            'sixieme': Unite.objects.filter(level__icontains='6ème'),
            'prepaIQ': Unite.objects.filter(level__icontains='Prépa IQ'),
            'autre': Unite.objects.filter(level__icontains='Autre'),
        }
    
    elif request.user.is_student:
        return redirect('lecon:subject_list_student')
    # elif request.user.is_teacher:
    #     return redirect('teacher:unites_list')

    else: 
        context = []

    return render(request, 'lecon/subject_list.html', context)


@login_required
@non_student_required
def create_subject(request):
    
    if request.method == 'POST':
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save(commit=False)
            subject.created_by = request.user
            subject.save()
            messages.success(request, 'Subject created successfully!')
            return redirect('lecon:subject_list')
    else:
        form = SubjectForm()
    return render(request, 'lecon/subject_form.html', {'form': form})


@login_required
@non_student_required
def create_chapter(request, unite_id):
    if request.user.is_student:
        messages.error ("Les étudiants n'ont pas l'autorisation de créer un chapitre")
        return redirect ('lecon:subject_detail', pk=unite_id)
    elif request.user.is_staff:
        unite = get_object_or_404(Unite, id=unite_id)
    else:
        messages.error("Vous n'avez aucune permission de créer de contenus dans cette page, veillez contact l'administrateur!")
        return redirect ('utilisateur:login')
    
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapter = form.save(commit=False)
            chapter.ue = unite  # Set the Unite from URL
            # chapter.prof = request.user.get_full_name() or request.user.username
            chapter.save()
            return redirect('lecon:subject_detail', pk=unite.id)
    else:
        # Pre-fill the form with default order
        last_chapter = Chapter.objects.filter(ue=unite).order_by('-order').first()
        initial_order = last_chapter.order + 1 if last_chapter else 1
        
        form = ChapterForm(initial={
            'order': initial_order,
            'is_active': True
        })
    
    return render(request, 'lecon/chapter_form.html', {
        'form': form,
        'unite': unite
    })


@login_required
@non_student_required
def edit_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    
    if request.method == 'POST' and request.user.is_staff:
        form = ChapterForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.success(request, 'Chapitre modifié avec succès!')
            return redirect('lecon:chapter_detail', subject_pk=chapter.ue.id, chapter_pk=chapter.id)
    else:
        form = ChapterForm(instance=chapter)
    
    return render(request, 'lecon/edit_chapter.html', {
        'form': form,
        'chapter': chapter
    })


@login_required
@non_student_required
def delete_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    subject_id = chapter.ue.id
    
    if request.method == 'POST' and request.user.is_sstaff:
        chapter.delete()
        messages.success(request, 'Chapitre supprimé avec succès!')
        return redirect('lecon:subject_detail', pk=subject_id)
    
    return render(request, 'lecon/delete_chapter.html', {'chapter': chapter})


@login_required
@non_student_required
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
    # flashcard_sets = FlashcardSet.objects.filter(title=chapter, created_by=request.user)
    # flashcard_sets_private = FlashcardSet.objects.filter(title=chapter, created_by=request.user, is_public=False)
    # flashcard_sets_public = FlashcardSet.objects.filter(title=chapter, is_public=True)
    
    # Get user's flashcard progress
    user_flashcard_progress = None
    total_flashcards = 0
    mastered_flashcards = 0
    
    # if request.user.is_authenticated:
    #     # Calculate flashcard progress
    #     flashcards = Flashcard.objects.filter(flashcard_set__title=chapter)
    #     total_flashcards = flashcards.count()
        
    #     if total_flashcards > 0:
    #         user_progress = UserProgress.objects.filter(
    #             user=request.user,
    #             flashcard__in=flashcards
    #         )
    #         mastered_flashcards = user_progress.filter(mastered=True).count()
    #         user_flashcard_progress = {
    #             'total': total_flashcards,
    #             'mastered': mastered_flashcards,
    #             'percentage': (mastered_flashcards / total_flashcards * 100) if total_flashcards > 0 else 0,
    #             'in_progress': user_progress.filter(mastered=False).count()
    #         }
    
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
        study_time_seconds = study_sessions.aggregate(Sum('duration_seconds'))['duration_seconds__sum'] or 0
    
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
        # 'flashcard_sets': flashcard_sets,
        # 'flashcard_sets_private': flashcard_sets_private,
        # 'flashcard_sets_public': flashcard_sets_public,
        # 'user_flashcard_progress': user_flashcard_progress,
        'study_time_hours': study_time_seconds // 3600,
        'study_time_minutes': (study_time_seconds % 3600) // 60,
    }
    
    return render(request, 'lecon/chapter_detail.html', context)


@login_required
def subject_detail(request, pk):
    unite = get_object_or_404(Unite, pk=pk)
    chapters_active = unite.chapters.filter(is_active=True).order_by('order')
    chapters = unite.chapters.all().order_by('order')
    sections = unite.unitesection_set.all().prefetch_related('chapters')
    
    # Calculate totals for dashboard
    total_mcqs = MCQ.objects.filter(chapter__ue=unite, chapter__is_active=True).count()
    total_qas = QuestionAnswer.objects.filter(chapter__ue=unite, chapter__is_active=True).count()
    total_tfs = TrueFalseQuiz.objects.filter(chapter__ue=unite, chapter__is_active=True).count()
    
    # Flashcard statistics for the entire subject
    # total_flashcard_sets = FlashcardSet.objects.filter(title__ue=unite).count()
    
    # Get all flashcards across all chapters in this subject
    # all_flashcards = Flashcard.objects.filter(flashcard_set__title__ue=unite)
    # total_flashcards = all_flashcards.count()
    
    # Calculate user's flashcard progress if student
    user_flashcard_progress = None
    # if request.user.is_student and total_flashcards > 0:
    #     user_progress = UserProgress.objects.filter(
    #         user=request.user,
    #         flashcard__in=all_flashcards
    #     )
    #     mastered_flashcards = user_progress.filter(mastered=True).count()
    #     user_flashcard_progress = {
    #         'total': total_flashcards,
    #         'mastered': mastered_flashcards,
    #         'percentage': (mastered_flashcards / total_flashcards * 100) if total_flashcards > 0 else 0,
    #         'sets_count': total_flashcard_sets
    #     }
    
    # Prepare chapters with study time and flashcard data
    chapters_with_data = []
    total_study_seconds = 0
    
    for chapter in chapters_active:
        chapter_data = {
            'chapter': chapter,
            'study_time_seconds': 0,
            'study_time_hours': 0,
            'study_time_minutes': 0,
            'flashcards_count': 0,
            'flashcard_mastery': 0
        }
        
        # Calculate flashcard data for this chapter
        # chapter_flashcards = Flashcard.objects.filter(flashcard_set__title=chapter)
        # chapter_data['flashcards_count'] = chapter_flashcards.count()
        
        if request.user.is_student:
            # Calculate study time for this chapter
            study_sessions = StudySession.objects.filter(
                user=request.user,
                chapter=chapter,
                completed=True
            )
            chapter_study_seconds = study_sessions.aggregate(Sum('duration_seconds'))['duration_seconds__sum'] or 0
            chapter_data['study_time_seconds'] = chapter_study_seconds
            chapter_data['study_time_hours'] = chapter_study_seconds // 3600
            chapter_data['study_time_minutes'] = (chapter_study_seconds % 3600) // 60
            
            total_study_seconds += chapter_study_seconds
            
            # Calculate flashcard mastery for this chapter
            # if chapter_data['flashcards_count'] > 0:
            #     user_chapter_progress = UserProgress.objects.filter(
            #         user=request.user,
            #         flashcard__in=chapter_flashcards
            #     )
            #     mastered = user_chapter_progress.filter(mastered=True).count()
            #     chapter_data['flashcard_mastery'] = (mastered / chapter_data['flashcards_count'] * 100) if chapter_data['flashcards_count'] > 0 else 0
        
        chapters_with_data.append(chapter_data)
    
    # Prepare sections with study time data
    sections_with_data = []
    for section in sections:
        section_data = {
            'section': section,
            'study_seconds': 0,
            'study_hours': 0,
            'study_minutes': 0,
            'chapter_count': section.chapters.count()
        }
        
        if request.user.is_student:
            # Calculate study time for all chapters in this section
            section_chapters = section.chapters.all()
            section_study_seconds = 0
            
            # Get study sessions for all chapters in this section in one query
            study_sessions = StudySession.objects.filter(
                user=request.user,
                chapter__in=section_chapters,
                completed=True
            ).values('chapter').annotate(total_seconds=Sum('duration_seconds'))
            
            # Sum up all study time for this section
            for session in study_sessions:
                section_study_seconds += session['total_seconds'] or 0
            
            section_data['study_seconds'] = section_study_seconds
            section_data['study_hours'] = section_study_seconds // 3600
            section_data['study_minutes'] = (section_study_seconds % 3600) // 60
        
        sections_with_data.append(section_data)
    
    # Get all flashcard sets for the "All Flashcards" view
    # all_flashcard_sets = FlashcardSet.objects.filter(title__ue=unite).select_related('title').order_by('title__order', 'created_at')
    # all_flashcard_sets_private = FlashcardSet.objects.filter(title__ue=unite, is_public=False, created_by=request.user).order_by('title__order', 'created_at')
    # all_flashcard_sets_public = FlashcardSet.objects.filter(title__ue=unite, is_public=True).order_by('title__order', 'created_at')
    
    # Calculate total study time for the subject (for student)
    total_study_time_hours = total_study_seconds // 3600
    total_study_time_minutes = (total_study_seconds % 3600) // 60
    
    # Calculate average scores for student
    mcq_score = 0
    qa_score = 0
    tf_score = 0
    
    if request.user.is_student:
        # Calculate MCQ average score
        mcq_results = MCQResult.objects.filter(student=request.user, chapter__ue=unite)
        if mcq_results.exists():
            mcq_score = mcq_results.aggregate(Avg('score'))['score__avg'] or 0
        
        # Calculate Q&A average score
        qa_results = QAResult.objects.filter(student=request.user, chapter__ue=unite)
        if qa_results.exists():
            qa_score = qa_results.aggregate(Avg('score'))['score__avg'] or 0
        
        # Calculate True/False average score
        tf_results = TrueFalseResult.objects.filter(student=request.user, chapter__ue=unite)
        if tf_results.exists():
            tf_score = tf_results.aggregate(Avg('score'))['score__avg'] or 0
    
    # Paginate chapters for collapsible view (show first 3)
    chapters_per_page = 3
    paginator = Paginator(chapters_with_data, chapters_per_page)
    page_number = request.GET.get('chapters_page', 1)
    chapters_page = paginator.get_page(page_number)
    
    context = {
        'unite': unite,
        'chapters_active': chapters_active,
        'chapters': chapters,
        'chapters_data': chapters_with_data,
        'chapters_page': chapters_page,
        'has_more_chapters': len(chapters_with_data) > chapters_per_page,
        'sections': sections,
        'sections_with_data': sections_with_data,
        'total_mcqs': total_mcqs,
        'total_qas': total_qas,
        'total_tfs': total_tfs,
        # 'total_flashcard_sets': total_flashcard_sets,
        # 'total_flashcards': total_flashcards,
        # 'all_flashcard_sets': all_flashcard_sets,
        # 'all_flashcard_sets_private': all_flashcard_sets_private,
        # 'all_flashcard_sets_public': all_flashcard_sets_public,
        'user_flashcard_progress': user_flashcard_progress,
        'total_study_time_hours': total_study_time_hours,
        'total_study_time_minutes': total_study_time_minutes,
        'mcq_score': mcq_score,
        'qa_score': qa_score,
        'tf_score': tf_score,
    }

    # if request.user.is_teacher:
    #     return redirect("teacher:chapitres_list", unite_id=pk)
    
    return render(request, 'lecon/subject_detail.html', context)


@login_required
@non_student_required
def create_section(request, unite_id):
    unite = get_object_or_404(Unite, id=unite_id)
    
    # Check permissions
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas l'autorisation de créer une section.")
        return redirect('lecon:subject_detail', pk=unite_id)
    
    if request.method == 'POST':
        form = UniteSectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.ue = unite
            section.save()
            form.save_m2m()  # Save the many-to-many relationship
            messages.success(request, f"Section '{section.title}' créée avec succès!")
            return redirect('lecon:subject_detail', pk=unite.id)
    else:
        # Filter chapters to only show those from the current unite
        form = UniteSectionForm(initial={'ue': unite})
        form.fields['chapters'].queryset = Chapter.objects.filter(ue=unite, is_active=True).order_by('order')
    
    return render(request, 'lecon/section_form.html', {
        'form': form,
        'unite': unite,
        'title': 'Créer une section'
    })


@login_required
def view_section(request, unite_id, section_id):
    unite = get_object_or_404(Unite, id=unite_id)
    section = get_object_or_404(UniteSection, id=section_id, ue=unite)
    
    # Get all chapters in this section
    chapters = section.chapters.all().order_by('order')
    
    # Calculate study time for this section if student
    section_study_seconds = 0
    if request.user.is_student:
        for chapter in chapters:
            study_sessions = StudySession.objects.filter(
                user=request.user,
                chapter=chapter,
                completed=True
            )
            section_study_seconds += sum(session.duration_seconds for session in study_sessions)
    
    context = {
        'unite': unite,
        'section': section,
        'chapters': chapters,
        'section_study_hours': section_study_seconds // 3600,
        'section_study_minutes': (section_study_seconds % 3600) // 60,
    }
    
    return render(request, 'lecon/section_detail.html', context)


@login_required
@non_student_required
def update_section(request, section_id):
    section = get_object_or_404(UniteSection, id=section_id)
    unite = section.ue
    
    # Check permissions
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas l'autorisation de modifier cette section.")
        return redirect('lecon:subject_detail', pk=unite.id)
    
    if request.method == 'POST':
        form = UniteSectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, f"Section '{section.title}' mise à jour avec succès!")
            return redirect('lecon:subject_detail', pk=unite.id)
    else:
        form = UniteSectionForm(instance=section)
        form.fields['chapters'].queryset = Chapter.objects.filter(ue=unite).order_by('order')
    
    return render(request, 'lecon/section_form.html', {
        'form': form,
        'unite': unite,
        'section': section,
        'title': 'Modifier la section'
    })


@login_required
@non_student_required
def delete_section(request, section_id):
    section = get_object_or_404(UniteSection, id=section_id)
    unite_id = section.ue.id
    
    # Check permissions
    if not request.user.is_staff:
        messages.error(request, "Seuls les administrateurs peuvent supprimer des sections.")
        return redirect('lecon:subject_detail', pk=unite_id)
    
    if request.method == 'POST':
        section_title = section.title
        section.delete()
        messages.success(request, f"Section '{section_title}' supprimée avec succès!")
        return redirect('lecon:subject_detail', pk=unite_id)
    
    return render(request, 'lecon/delete_section.html', {
        'section': section
    })


@login_required
@non_student_required
def update_unite(request, unite_id):
    unite = get_object_or_404(Unite, id=unite_id)

    if not request.user.is_superuser:
        messages.error(request, "Vous n'êtes pas autorisé à modifier cette unité.")
        return redirect('lecon:my_subjects')

    if request.method == 'POST':
        form = SubjectForm(request.POST, instance=unite)
        if form.is_valid():
            form.save()
            messages.success(request, "Unité mise à jour avec succès.")
            return redirect('lecon:my_subjects')
    else:
        form = SubjectForm(instance=unite)

    return render(request, 'lecon/subject_form.html', {
        'form': form,
        'unite': unite,
        'is_update': True,
    })


@login_required
@require_http_methods(["POST"])
def delete_unite(request, unite_id):
    unite = get_object_or_404(Unite, id=unite_id)

    if not request.user.is_superuser:
        messages.error(request, "Vous n'avez pas la permission de supprimer cette Unité d'enseignement.")
        return redirect('lecon:my_subjects')

    unite.delete()
    messages.success(request, "Unité supprimée avec succès.")
    return redirect('lecon:subject_list')


@login_required
def chapter_search_view(request):
    user = request.user
    form = ChapterSearchForm(request.GET)
    chapters = Chapter.objects.select_related('ue')

    if form.is_valid():
        q = form.cleaned_data.get('q', '').strip()
        level = form.cleaned_data.get('level')
        semester = form.cleaned_data.get('semester')
        prof = form.cleaned_data.get('prof', '').strip()

        # 1️⃣ If search query exists, find chapters via Copy.content
        if q:
            matching_chapter_ids = Copy.objects.filter(
                content__icontains=q
            ).values_list('chapter_id', flat=True).distinct()
            
            chapters = chapters.filter(id__in=matching_chapter_ids)

        # 2️⃣ Apply dropdown filters
        if level:
            chapters = chapters.filter(ue__level=level)
        if semester:
            chapters = chapters.filter(ue__semester=semester)
        if prof:
            chapters = chapters.filter(prof__icontains=prof)

    # 📄 Pagination (preserves filter state)
    paginator = Paginator(chapters, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Remove 'page' from query string for clean pagination links
    get_params = request.GET.copy()
    if 'page' in get_params:
        get_params.pop('page')
    base_query = get_params.urlencode()

    return render(request, 'lecon/search_results.html', {
        'form': form,
        'page_obj': page_obj,
        'base_query': base_query,
        'user': user,
    })


def get_heading_level_int(copy):
    """Convert heading_level CharField to integer"""
    try:
        return int(copy.heading_level) if copy.heading_level else 9
    except (ValueError, TypeError):
        return 9


def get_hierarchical_section(seed_copy):
    """Get all copies from seed until next heading of same level"""
    seed_level = get_heading_level_int(seed_copy)
    chapter_copies = Copy.objects.filter(chapter=seed_copy.chapter).order_by('id')
    result = []
    collecting = False
    
    for copy in chapter_copies:
        if copy.id == seed_copy.id:
            collecting = True
            result.append(copy)
            continue
        if not collecting:
            continue
        # Stop if we find a heading with level <= seed_level
        if copy.heading and get_heading_level_int(copy) <= seed_level:
            break
        result.append(copy)
    
    return result

@login_required
def heading_comparative_search(request):
    """Main view for the search page"""
    return render(request, 'lecon/heading_search.html')


@require_http_methods(["GET"])
def ajax_get_unites_by_level(request):
    """Return unites filtered by level as JSON"""
    level = request.GET.get('level', '').strip()
    print(f"🔍 DEBUG: ajax_get_unites_by_level called with level: '{level}'")
    
    if not level:
        return JsonResponse({'unites': [], 'debug': 'No level provided'})
    
    # Try exact match first
    unites = Unite.objects.filter(level=level).order_by('title')
    print(f"📊 DEBUG: Found {unites.count()} unites with exact match")
    
    if not unites.exists():
        # Try case-insensitive
        unites = Unite.objects.filter(level__iexact=level).order_by('title')
        print(f"📊 DEBUG: Found {unites.count()} unites with case-insensitive match")
    
    data = [{'id': u.id, 'title': u.title} for u in unites]
    print(f"✅ DEBUG: Returning {len(data)} unites")
    
    return JsonResponse({'unites': data})


@require_http_methods(["GET"])
def heading_search_api(request):
    """AJAX endpoint for heading search"""
    level = request.GET.get('level')
    unite_id = request.GET.get('unite')
    query = request.GET.get('heading_query', '').strip()
    
    print(f"🔍 DEBUG: heading_search_api called - level: {level}, unite_id: {unite_id}, query: {query}")
    
    if not level or not unite_id or not query:
        print(f"⚠️ DEBUG: Missing parameters - level:{level}, unite_id:{unite_id}, query:{query}")
        return JsonResponse({'results': []})
    
    # Get the unite object
    try:
        unite = Unite.objects.get(id=unite_id)
        print(f"✅ DEBUG: Found unite: {unite.title}")
    except Unite.DoesNotExist:
        print(f"❌ DEBUG: Unite not found with id: {unite_id}")
        return JsonResponse({'error': 'Unité non trouvée'}, status=404)
    
    # Search for headings
    seeds = Copy.objects.filter(
        heading__icontains=query,
        chapter__ue=unite,
        chapter__is_active=True
    ).select_related('chapter').order_by('chapter__id', 'id')
    
    print(f"📊 DEBUG: Found {seeds.count()} seeds for query '{query}'")
    
    results = []
    for seed in seeds:
        hierarchical = get_hierarchical_section(seed)
        print(f"📝 DEBUG: Seed '{seed.heading}' has {len(hierarchical)} hierarchical copies")
        
        results.append({
            'chapter_title': seed.chapter.title,
            'seed_heading': seed.heading,
            'seed_level': get_heading_level_int(seed),
            'rows': [
                {
                    'id': c.id,
                    'heading': c.heading,
                    'heading_level': get_heading_level_int(c),
                    'content': c.content,
                    'explanation': c.explanation,
                    'image_url': c.image.url if c.image else None,
                    'table': c.table,
                    'is_qe': c.is_qe,
                }
                for c in hierarchical
            ]
        })
    
    print(f"✅ DEBUG: Returning {len(results)} results")
    return JsonResponse({'results': results})


@csrf_exempt
@require_http_methods(["POST"])
def download_results_pdf(request):
    """Generate HTML page that users can print to PDF directly from browser"""
    try:
        data = json.loads(request.body)
        results = data.get('results', [])
        query = data.get('query', '')
        unite_name = data.get('unite_name', '')
        level_name = data.get('level_name', '')
        
        context = {
            'results': results,
            'query': query,
            'unite_name': unite_name,
            'level_name': level_name,
            'generated_date': datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        
        # Use a print-friendly template
        template = get_template('lecon/pdf_print_template.html')
        html_string = template.render(context)
        
        # Return HTML that browser can print to PDF
        response = HttpResponse(html_string, content_type='text/html')
        filename = f"recherche_{query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return HttpResponse(f"Error: {str(e)}", status=500)


def content_search_api_grouped(request):
    """AJAX endpoint - groups all matches from same chapter into one result"""
    level = request.GET.get('level')
    unite_id = request.GET.get('unite')
    query = request.GET.get('content_query', '').strip()
    
    print(f"🔍 DEBUG: Content search - level: {level}, unite_id: {unite_id}, query: {query}")
    
    if not level or not unite_id or not query:
        return JsonResponse({'results': []})
    
    # Get the unite object
    try:
        unite = Unite.objects.get(id=unite_id)
    except Unite.DoesNotExist:
        return JsonResponse({'error': 'Unité non trouvée'}, status=404)
    
    # Get all copies in this unite
    copies = Copy.objects.filter(
        chapter__ue=unite,
        chapter__is_active=True
    ).select_related('chapter').order_by('chapter__id', 'id')
    
    # Find all copies that contain the search term
    matching_copies = []
    for copy in copies:
        if copy.content:
            content_str = json.dumps(copy.content, ensure_ascii=False).lower()
            if query.lower() in content_str:
                matching_copies.append(copy)
    
    # Group by chapter
    chapters_dict = {}
    
    for match_copy in matching_copies:
        chapter_id = match_copy.chapter.id
        
        if chapter_id not in chapters_dict:
            chapters_dict[chapter_id] = {
                'chapter_title': match_copy.chapter.title,
                'all_copies': [],  # Will store all unique copies from all matches
                'matches_info': []  # Store info about each match
            }
        
        # Get hierarchical section for this match
        hierarchical_section = get_hierarchical_section(match_copy)
        
        # Add all copies from this section to the chapter's collection (avoid duplicates)
        for copy in hierarchical_section:
            # Check if this copy already exists in all_copies
            if copy.id not in [c['id'] for c in chapters_dict[chapter_id]['all_copies']]:
                chapters_dict[chapter_id]['all_copies'].append({
                    'id': copy.id,
                    'heading': copy.heading,
                    'heading_level': get_heading_level_int(copy),
                    'content': copy.content,
                    'explanation': copy.explanation,
                    'image_url': copy.image.url if copy.image else None,
                    'table': copy.table,
                    'is_qe': copy.is_qe,
                })
        
        # Store match info
        chapters_dict[chapter_id]['matches_info'].append({
            'match_id': match_copy.id,
            'matching_heading': match_copy.heading or "Contenu trouvé"
        })
    
    # Build results - one per chapter with all matches
    results = []
    for chapter_data in chapters_dict.values():
        # Sort copies by id to maintain order
        sorted_copies = sorted(chapter_data['all_copies'], key=lambda x: x['id'])
        
        # Create matching headings list for display
        matching_headings = list(set([m['matching_heading'] for m in chapter_data['matches_info']]))
        
        results.append({
            'chapter_title': chapter_data['chapter_title'],
            'matching_headings': matching_headings,  # List of all headings that had matches
            'match_count': len(chapter_data['matches_info']),
            'rows': sorted_copies
        })
    
    return JsonResponse({'results': results})


def content_comparative_search(request):
    """Main view for content search page"""
    form = ContentFilterForm()
    return render(request, 'lecon/content_search.html', {'form': form})



@login_required
@non_student_required
def ue_list(request):
    ues = Unite.objects.all().order_by('level')

    return render (request, 'lecon/ue_list.html', {'ues':ues})


@login_required
@non_student_required
def chapter_list_view(request, ue_id):
    ue = Unite.objects.get(id=ue_id)
    chapters = Chapter.objects.filter(ue=ue).order_by('title')
    active = Chapter.objects.filter(ue=ue, is_active=True).count()
    non_active = chapters.count()-active

    context = {
        'ue': ue,
        'chapters': chapters,
        'active': active,
        'non_active': non_active
    }

    return render(request, 'lecon/chapter_list.html', context)


def chapter_element(request, ue_id):
    ue = Unite.objects.get(id=ue_id)
    chapters = Chapter.objects.filter(ue=ue).order_by('order')

    context = {
        'ue': ue,
        'chapters': chapters,
    }

    return render(request, 'lecon/chapter_element.html', context)
