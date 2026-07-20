import os
import re
import csv
from pathlib import Path
from django.conf import settings
from django.core.files import File
from lecon.models import Unite, Chapter as LessonChapter
from lessoncopy.models import Copy, Importer
from lessoncopy.utils import extract_docx_to_model
from quizzes.models import MCQ, QuestionAnswer, TrueFalseQuiz
# from quizlet_copy.models import FlashcardSet, Flashcard
from .utils import (
    get_unite_folders, get_chapter_files_for_unite,
    get_shifted_files_for_chapter, get_exercise_files_for_chapter,
    get_chapter_title_from_filename, normalize_french, clean_filename_for_title
)


def sanitize_filename(title):
    """Convert a title to a safe filename."""
    s = re.sub(r'[^\w\s-]', '', title)
    s = re.sub(r'[-\s]+', '-', s)
    return s.strip('-')


# ---------- Unite import ----------
def import_unites_from_level(level_name):
    """Create Unite objects from folder names under splitted/level_name."""
    from .utils import get_unite_folders
    stats = {'created': 0, 'skipped': 0, 'errors': []}
    try:
        unite_folders = get_unite_folders(level_name)
    except Exception as e:
        stats['errors'].append(f"Could not list unite folders for level {level_name}: {str(e)}")
        return stats

    for folder in unite_folders:
        norm_title = normalize_french(folder)
        # Check if Unite already exists with same level and title
        exists = Unite.objects.filter(level__iexact=level_name, title__iexact=norm_title).exists()
        if exists:
            stats['skipped'] += 1
            continue
        try:
            Unite.objects.create(
                level=level_name,
                title=folder,  # keep original case
                semester='S1'   # default
            )
            stats['created'] += 1
        except Exception as e:
            stats['errors'].append(f"Unite '{folder}': {str(e)}")
    return stats


def import_unites_from_level_bulk(level_names):
    aggregated = {'created': 0, 'skipped': 0, 'errors': []}
    for level in level_names:
        stats = import_unites_from_level(level)
        aggregated['created'] += stats['created']
        aggregated['skipped'] += stats['skipped']
        aggregated['errors'].extend(stats['errors'])
    return aggregated


# ---------- Chapter import ----------
def import_chapters_from_unite(unite):
    """Create Chapter objects from .docx files in splitted/level/unite/."""
    stats = {'created': 0, 'skipped': 0, 'errors': []}
    try:
        files = get_chapter_files_for_unite(unite.level, unite.title, subdir='splitted')
    except Exception as e:
        stats['errors'].append(f"Could not list chapter files for unite {unite.id}: {str(e)}")
        return stats

    for file_path in files:
        title = clean_filename_for_title(file_path.name)
        norm_title = normalize_french(title)
        # Check if Chapter already exists for this unite
        exists = LessonChapter.objects.filter(ue=unite, title__iexact=norm_title).exists()
        if exists:
            stats['skipped'] += 1
            continue
        try:
            # Try to extract order from filename (e.g., 001_...)
            order = None
            match = re.match(r'^(\d+)_', file_path.stem)
            if match:
                order = int(match.group(1))
            LessonChapter.objects.create(
                ue=unite,
                title=title,
                order=order,
                is_active=True
            )
            stats['created'] += 1
        except Exception as e:
            stats['errors'].append(f"Chapter '{title}': {str(e)}")
    return stats


def import_chapters_from_unites_bulk(unite_ids, user):
    aggregated = {'created': 0, 'skipped': 0, 'errors': []}
    for uid in unite_ids:
        try:
            unite = Unite.objects.get(id=uid)
            stats = import_chapters_from_unite(unite)
            aggregated['created'] += stats['created']
            aggregated['skipped'] += stats['skipped']
            aggregated['errors'].extend(stats['errors'])
        except Unite.DoesNotExist:
            aggregated['errors'].append(f"Unite with id {uid} not found.")
    return aggregated


# ---------- Copy import (from shifted down) ----------
def import_copies_for_chapter(chapter, user):
    stats = {
        'importers_created': 0,
        'copies_created': 0,
        'files_found': 0,
        'files_matched': 0,
        'errors': [],
        'debug': []
    }
    try:
        files = get_shifted_files_for_chapter(chapter.ue.level, chapter.ue.title, chapter.title)
        stats['files_found'] = len(files)
    except Exception as e:
        stats['errors'].append(f"Could not list shifted files: {str(e)}")
        return stats

    norm_chapter = normalize_french(chapter.title)
    stats['debug'].append(f"Looking for chapter '{chapter.title}' (normalized: {norm_chapter})")

    for file_path in files:
        file_title_base = get_chapter_title_from_filename(file_path.name)
        norm_file = normalize_french(file_title_base)
        stats['debug'].append(f"Found file: {file_path.name} → base title '{file_title_base}' (norm: {norm_file})")

        if norm_file != norm_chapter:
            stats['debug'].append(f"  Skipped: does not match chapter")
            continue

        stats['files_matched'] += 1
        try:
            # Create Importer record
            importer = Importer(
                chapter=chapter,
                file_type='docx',
                title=f"Version: {file_path.stem}",
                processed=False
            )
            with open(file_path, 'rb') as f:
                importer.file.save(file_path.name, File(f), save=False)
            importer.save()
            stats['importers_created'] += 1
            stats['debug'].append(f"  Created Importer {importer.id}")

            # Extract copies
            extract_docx_to_model(importer.file.path, chapter.id, importer)
            importer.processed = True
            importer.save()
            copies = Copy.objects.filter(importer=importer).count()
            stats['copies_created'] += copies
            stats['debug'].append(f"  Created {copies} copies")

        except Exception as e:
            stats['errors'].append(f"File {file_path.name}: {str(e)}")
    return stats


def import_copies_for_chapters_bulk(chapter_ids, user):
    aggregated = {'importers_created': 0, 'copies_created': 0, 'errors': []}
    for cid in chapter_ids:
        try:
            chapter = LessonChapter.objects.get(id=cid)
            stats = import_copies_for_chapter(chapter, user)
            aggregated['importers_created'] += stats['importers_created']
            aggregated['copies_created'] += stats['copies_created']
            aggregated['errors'].extend(stats['errors'])
        except LessonChapter.DoesNotExist:
            aggregated['errors'].append(f"Chapter {cid} not found.")
    return aggregated


# ---------- Exercise file generation ----------
def create_exercise_files_for_chapter(chapter):
    """Create empty exercise files for a chapter in the exercices folder."""
    root = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_EXERCICES_DIR
    level = chapter.ue.level
    unite = chapter.ue.title
    chapter_title = chapter.title
    folder_path = root / level / unite / chapter_title
    folder_path.mkdir(parents=True, exist_ok=True)

    safe_title = sanitize_filename(chapter_title)

    templates = {
        f'mcq-{safe_title}.csv': "question,option1,option2,option3,option4,correct,explanation\n",
        f'qa-{safe_title}.csv': "question,answer,explanation\n",
        f'tf-{safe_title}.csv': "question,answer,explanation\n",
        f'flashcard-{safe_title}.csv': "term,definition\n",
        f'terminology-{safe_title}.csv': "term,meaning,hint\n",
        f'summary-{safe_title}.txt': "# Résumé du chapitre\n\n",
        f'clinical_case-{safe_title}.txt': "# Cas clinique\n\n",
    }
    created = []
    for filename, content in templates.items():
        file_path = folder_path / filename
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            created.append(filename)
    return created


def create_exercise_files_for_chapters_bulk(chapter_ids):
    aggregated = {'folders_created': 0, 'files_created': 0, 'errors': []}
    for cid in chapter_ids:
        try:
            chapter = LessonChapter.objects.get(id=cid)
            created = create_exercise_files_for_chapter(chapter)
            aggregated['folders_created'] += 1
            aggregated['files_created'] += len(created)
        except LessonChapter.DoesNotExist:
            aggregated['errors'].append(f"Chapter {cid} not found.")
        except Exception as e:
            aggregated['errors'].append(f"Chapter {cid}: {str(e)}")
    return aggregated


# ---------- Exercise import (from exercices folder) ----------
def process_mcq_file(file_path, chapter, user):
    count = 0
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    MCQ.objects.create(
                        chapter=chapter,
                        created_by=user,
                        question=row.get('question', '').strip(),
                        option1=row.get('option1', '').strip(),
                        option2=row.get('option2', '').strip(),
                        option3=row.get('option3', '').strip() or None,
                        option4=row.get('option4', '').strip() or None,
                        correct_option=int(row.get('correct') or row.get('answer') or 1),
                        explanation=row.get('explanation') or row.get('explication') or '',
                        time_limit=60,
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"Erreur lecture fichier: {str(e)}")
    return count, errors


def process_qa_file(file_path, chapter, user):
    count = 0
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    QuestionAnswer.objects.create(
                        chapter=chapter,
                        created_by=user,
                        question=row.get('question', '').strip(),
                        sample_answer=row.get('answer') or row.get('réponse') or '',
                        explanation=row.get('explanation') or row.get('explication') or '',
                        time_limit=300,
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"Erreur lecture fichier: {str(e)}")
    return count, errors


def process_tf_file(file_path, chapter, user):
    count = 0
    errors = []
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    answer_text = row.get('answer') or row.get('correct') or ''
                    bool_answer = answer_text.lower() in ('true', '1', 'yes', 'vrai')
                    TrueFalseQuiz.objects.create(
                        chapter=chapter,
                        created_by=user,
                        question=row.get('question', '').strip(),
                        answer=bool_answer,
                        explanation=row.get('explanation') or row.get('explication') or '',
                        time_limit=int(row.get('time_limit', 30)),
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"Erreur lecture fichier: {str(e)}")
    return count, errors


# def process_flashcard_file(file_path, chapter, user):
#     count = 0
#     errors = []
#     try:
#         # Get or create a flashcard set for this chapter (public by default for staff)
#         flashcard_set, created = FlashcardSet.objects.get_or_create(
#             title=chapter,
#             is_public=True,
#             defaults={'created_by': user, 'description': ''}
#         )
#         with open(file_path, 'r', encoding='utf-8-sig') as f:
#             reader = csv.DictReader(f)
#             for row_num, row in enumerate(reader, start=2):
#                 try:
#                     Flashcard.objects.create(
#                         flashcard_set=flashcard_set,
#                         term=row.get('term', '').strip() or row.get('front', '').strip,
#                         definition=row.get('definition', '') or row.get('meaning', '') or row.get('back', ''),
#                     ) 
#                     count += 1
#                 except Exception as e:
#                     errors.append(f"Ligne {row_num}: {str(e)}")
#     except Exception as e:
#         errors.append(f"Erreur lecture fichier: {str(e)}")
#     return count, errors


def process_summary_file(file_path, chapter, user):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        from lessoncopy.models import ResumeIA
        ResumeIA.objects.create(
            chapitre=chapter,
            resume=content,
        )
        return 1, []
    except Exception as e:
        return 0, [f"Erreur lecture résumé: {str(e)}"]


def import_exercises_for_chapter(chapter, user):
    """Import all exercise files for a chapter."""
    stats = {
        'mcq': 0, 'qa': 0, 'tf': 0,
        # 'flashcard': 0, 'terminology': 0,
        'summary': 0, #'clinical': 0,
        'errors': []
    }
    try:
        files = get_exercise_files_for_chapter(chapter.ue.level, chapter.ue.title, chapter.title)
    except Exception as e:
        stats['errors'].append(f"Could not list exercise files: {str(e)}")
        return stats

    for file_type, file_path in files.items():
        try:
            if file_type == 'mcq':
                cnt, errs = process_mcq_file(file_path, chapter, user)
                stats['mcq'] += cnt
                stats['errors'].extend(errs)
            elif file_type == 'qa':
                cnt, errs = process_qa_file(file_path, chapter, user)
                stats['qa'] += cnt
                stats['errors'].extend(errs)
            elif file_type == 'tf':
                cnt, errs = process_tf_file(file_path, chapter, user)
                stats['tf'] += cnt
                stats['errors'].extend(errs)
            # elif file_type == 'flashcard':
            #     cnt, errs = process_flashcard_file(file_path, chapter, user)
            #     stats['flashcard'] += cnt
            #     stats['errors'].extend(errs)
            elif file_type == 'summary':
                cnt, errs = process_summary_file(file_path, chapter, user)
                stats['summary'] += cnt
                stats['errors'].extend(errs)
            # elif file_type == 'clinical':
            #     cnt, errs = process_clinical_file(...)
            #     stats['clinical'] += cnt
            #     stats['errors'].extend(errs)
        except Exception as e:
            stats['errors'].append(f"Error processing {file_path.name}: {str(e)}")
    return stats


def import_exercises_for_chapters_bulk(chapter_ids, user):
    aggregated = {
        'mcq': 0, 'qa': 0, 'tf': 0,
        # 'flashcard': 0, 'terminology': 0,
        'summary': 0, #'clinical': 0,
        'errors': []
    }
    for cid in chapter_ids:
        try:
            chapter = LessonChapter.objects.get(id=cid)
            stats = import_exercises_for_chapter(chapter, user)
            aggregated['mcq'] += stats.get('mcq', 0)
            aggregated['qa'] += stats.get('qa', 0)
            aggregated['tf'] += stats.get('tf', 0)
            # aggregated['flashcard'] += stats.get('flashcard', 0)
            # aggregated['terminology'] += stats.get('terminology', 0)
            aggregated['summary'] += stats.get('summary', 0)
            # aggregated['clinical'] += stats.get('clinical', 0)
            aggregated['errors'].extend(stats.get('errors', []))
        except LessonChapter.DoesNotExist:
            aggregated['errors'].append(f"Chapter {cid} not found.")
    return aggregated

