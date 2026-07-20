from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from subscriptions.decorators import non_student_required
from lecon.models import Unite, Chapter as LessonChapter
from .utils import get_level_folders, get_folder_stats
from . import importers
from django.conf import settings
from lessoncopy.models import Importer
from pathlib import Path
from .utils import get_level_folders, get_folder_stats, get_exercise_folder_for_chapter


# ---------- Dashboard ----------
@login_required
@non_student_required
def dashboard(request):
    levels = get_level_folders()
    unites = Unite.objects.all().select_related()
    chapters = LessonChapter.objects.select_related('ue').all()
    folder_stats = get_folder_stats()
    return render(request, 'bulk_import/dashboard.html', {
        'levels': levels,
        'unites': unites,
        'chapters': chapters,
        'folder_stats': folder_stats,
        'bulk_import_root': settings.BULK_IMPORT_ROOT,
    })


# ---------- Level list ----------
@login_required
@non_student_required
def level_list(request):
    levels = get_level_folders()
    return render(request, 'bulk_import/level_list.html', {'levels': levels})


# ---------- Unite list for a level ----------
@login_required
@non_student_required
def unite_list(request, level_name):
    unites = Unite.objects.filter(level=level_name).order_by('title')
    return render(request, 'bulk_import/unite_list.html', {
        'level_name': level_name,
        'unites': unites,
    })


# ---------- Chapter list for a unite ----------
# @login_required
# @non_student_required
# def chapter_list(request, unite_id):
#     unite = get_object_or_404(Unite, id=unite_id)
#     chapters = unite.chapters.all().order_by('order')

#     # Annotate chapters
#     for chapter in chapters:
#         chapter.has_copies = Importer.objects.filter(chapter=chapter).exists()
#         # Check if exercise folder exists and has files
#         exercise_path = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_EXERCICES_DIR / unite.level / unite.title / chapter.title
#         chapter.has_exercise_files = exercise_path.exists() and any(exercise_path.iterdir())

#     return render(request, 'bulk_import/chapter_list.html', {
#         'unite': unite,
#         'chapters': chapters,
#     })




@login_required
@non_student_required
def chapter_list(request, unite_id):
    unite = get_object_or_404(Unite, id=unite_id)
    chapters = unite.chapters.all().order_by('order')
    
    # Annotate chapters
    for chapter in chapters:
        chapter.has_copies = Importer.objects.filter(chapter=chapter).exists()
        
        # 2. FIX: Use the robust folder finder instead of exact Path matching
        exercise_folder = get_exercise_folder_for_chapter(unite.level, unite.title, chapter.title)
        chapter.has_exercise_files = exercise_folder is not None and any(exercise_folder.iterdir())
        
    return render(request, 'bulk_import/chapter_list.html', {
        'unite': unite,
        'chapters': chapters,
    })


# ---------- Single item imports ----------
@login_required
@non_student_required
def import_level_unites(request, level_name):
    stats = importers.import_unites_from_level(level_name)
    messages.success(request, f"Import level '{level_name}' completed.")
    return render(request, 'bulk_import/import_report.html', {
        'title': f"Import Unites for {level_name}",
        'stats': stats,
        'back_url': reverse('bulk_import:level_list')
    })


@login_required
@non_student_required
def import_unite_chapters(request, unite_id):
    unite = get_object_or_404(Unite, id=unite_id)
    stats = importers.import_chapters_from_unite(unite)
    messages.success(request, f"Import chapters for Unite '{unite.title}' completed.")
    return render(request, 'bulk_import/import_report.html', {
        'title': f"Import Chapters for {unite.title}",
        'stats': stats,
        'back_url': reverse('bulk_import:unite_list', args=[unite.level])
    })


@login_required
@non_student_required
def import_chapter_copies(request, chapter_id):
    chapter = get_object_or_404(LessonChapter, id=chapter_id)
    stats = importers.import_copies_for_chapter(chapter, request.user)
    messages.success(request, f"Import copies for Chapter '{chapter.title}' completed.")
    return render(request, 'bulk_import/import_report.html', {
        'title': f"Import Copies for {chapter.title}",
        'stats': stats,
        'back_url': reverse('bulk_import:chapter_list', args=[chapter.ue.id])
    })


@login_required
@non_student_required
def import_chapter_exercises(request, chapter_id):
    chapter = get_object_or_404(LessonChapter, id=chapter_id)
    stats = importers.import_exercises_for_chapter(chapter, request.user)
    messages.success(request, f"Import exercises for Chapter '{chapter.title}' completed.")
    return render(request, 'bulk_import/import_report.html', {
        'title': f"Import Exercises for {chapter.title}",
        'stats': stats,
        'back_url': reverse('bulk_import:chapter_list', args=[chapter.ue.id])
    })


# ---------- Bulk imports (AJAX + fallback) ----------
@login_required
@non_student_required
@require_POST
def bulk_import_unites(request):
    raw_levels = request.POST.getlist('selected_levels')
    level_names = [l for l in raw_levels if l and l.strip()]
    if not level_names:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No levels selected.'})
        messages.error(request, "No levels selected.")
        return redirect('bulk_import:level_list')

    stats = importers.import_unites_from_level_bulk(level_names)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('bulk_import/import_report_modal_content.html', {
            'title': 'Bulk Import Unites',
            'stats': stats
        })
        return JsonResponse({'success': True, 'html': html})
    return render(request, 'bulk_import/import_report.html', {
        'title': 'Bulk Import Unites',
        'stats': stats,
        'back_url': reverse('bulk_import:level_list')
    })


@login_required
@non_student_required
@require_POST
def bulk_import_chapters(request):
    raw_ids = request.POST.getlist('selected_unites')
    unite_ids = []
    for rid in raw_ids:
        if rid and rid.strip():
            try:
                unite_ids.append(int(rid.strip()))
            except ValueError:
                continue
    if not unite_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No unites selected.'})
        messages.error(request, "No unites selected.")
        return redirect(request.META.get('HTTP_REFERER', 'bulk_import:level_list'))

    stats = importers.import_chapters_from_unites_bulk(unite_ids, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('bulk_import/import_report_modal_content.html', {
            'title': 'Bulk Import Chapters',
            'stats': stats
        })
        return JsonResponse({'success': True, 'html': html})
    return render(request, 'bulk_import/import_report.html', {
        'title': 'Bulk Import Chapters',
        'stats': stats,
        'back_url': request.META.get('HTTP_REFERER', reverse('bulk_import:level_list'))
    })


@login_required
@non_student_required
@require_POST
def bulk_import_copies(request):
    raw_ids = request.POST.getlist('selected_chapters')
    chapter_ids = []
    for rid in raw_ids:
        if ',' in rid:
            chapter_ids.extend([x.strip() for x in rid.split(',') if x.strip()])
        else:
            if rid and rid.strip():
                chapter_ids.append(rid.strip())

    # Convert to integers
    valid_ids = []
    for cid in chapter_ids:
        try:
            valid_ids.append(int(cid))
        except ValueError:
            continue

    if not valid_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No valid chapters selected.'})
        messages.error(request, "No valid chapters selected.")
        return redirect(request.META.get('HTTP_REFERER', 'bulk_import:level_list'))

    stats = importers.import_copies_for_chapters_bulk(valid_ids, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('bulk_import/import_report_modal_content.html', {
            'title': 'Bulk Import Copies',
            'stats': stats
        })
        return JsonResponse({'success': True, 'html': html})
    # fallback
    return render(request, 'bulk_import/import_report.html', {
        'title': 'Bulk Import Copies',
        'stats': stats,
        'back_url': request.META.get('HTTP_REFERER', reverse('bulk_import:level_list'))
    })


@login_required
@non_student_required
@require_POST
def bulk_import_exercises(request):
    raw_ids = request.POST.getlist('selected_chapters')
    chapter_ids = []
    for rid in raw_ids:
        if rid and rid.strip():
            try:
                chapter_ids.append(int(rid.strip()))
            except ValueError:
                continue
    if not chapter_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No chapters selected.'})
        messages.error(request, "No chapters selected.")
        return redirect(request.META.get('HTTP_REFERER', 'bulk_import:level_list'))

    stats = importers.import_exercises_for_chapters_bulk(chapter_ids, request.user)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('bulk_import/import_report_modal_content.html', {
            'title': 'Bulk Import Exercises',
            'stats': stats
        })
        return JsonResponse({'success': True, 'html': html})
    return render(request, 'bulk_import/import_report.html', {
        'title': 'Bulk Import Exercises',
        'stats': stats,
        'back_url': request.META.get('HTTP_REFERER', reverse('bulk_import:level_list'))
    })


@login_required
@non_student_required
@require_POST
def generate_chapter_exercise_files(request):
    raw_ids = request.POST.getlist('selected_chapters')
    chapter_ids = []
    for rid in raw_ids:
        if rid and rid.strip():
            # Split by comma in case multiple IDs are sent as one string
            for part in rid.split(','):
                part = part.strip()
                if part:
                    try:
                        chapter_ids.append(int(part))
                    except ValueError:
                        continue
    if not chapter_ids:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'No valid chapters selected.'})
        messages.error(request, "No valid chapters selected.")
        return redirect(request.META.get('HTTP_REFERER', 'bulk_import:level_list'))

    stats = importers.create_exercise_files_for_chapters_bulk(chapter_ids)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        html = render_to_string('bulk_import/import_report_modal_content.html', {
            'title': 'Generate Exercise Files',
            'stats': stats
        })
        return JsonResponse({'success': True, 'html': html})
    return render(request, 'bulk_import/import_report.html', {
        'title': 'Generate Exercise Files',
        'stats': stats,
        'back_url': request.META.get('HTTP_REFERER', reverse('bulk_import:level_list'))
    })

