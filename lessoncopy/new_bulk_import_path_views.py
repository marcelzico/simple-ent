import os
import csv
from pathlib import Path
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from lecon.models import Unite, Chapter
from quizzes.models import MCQ, QuestionAnswer, TrueFalseQuiz
from . models import ResumeIA, Copy
from quizlet_copy.models import FlashcardSet, Flashcard
from .forms import ChapterDataFolderImportForm
import unicodedata

def normalize_french(text):
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    lowered = without_accents.lower()
    lowered = lowered.replace('œ', 'oe').replace('æ', 'ae')
    return lowered.strip()

# ---------- File type detection and handlers ----------
def process_mcq_file(file_path, chapter, user):
    """Import MCQ from CSV file."""
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
                        time_limit= 60,
                    )
                    count += 1
                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"Erreur lecture fichier: {str(e)}")
    return count, errors


def process_qa_file(file_path, chapter, user):
    """Import QuestionAnswer from CSV."""
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
    """Import TrueFalseQuiz from CSV."""
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


def process_flashcard_file(file_path, chapter, user):
    """Import Flashcards from CSV."""
    count = 0
    errors = []
    try:
        # Get or create a flashcard set for this chapter
        flashcard_set, created = FlashcardSet.objects.get_or_create(
            title=chapter,  # if title is FK; otherwise use chapter and a default name
            is_public=True,
            defaults={'created_by': user, 'description': ''}
        )
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):
                try:
                    Flashcard.objects.create(
                        flashcard_set=flashcard_set,
                        term=row.get('term', '').strip() or row.get('front', '').strip(),
                        definition=row.get('definition', '') or row.get('meaning', '') or row.get('back', ''),
                    )
                    count += 1 
                except Exception as e:
                    errors.append(f"Ligne {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"Erreur lecture fichier: {str(e)}")
    return count, errors


def process_summary_file(file_path, chapter, user):
    """Import Summary from plain text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ResumeIA.objects.create(
            chapter=chapter,
            content=content,
            created_by=user
        )
        return 1, []
    except Exception as e:
        return 0, [f"Erreur lecture résumé: {str(e)}"]


# ----------------------------------------------------------------------
# Core recursive processing
# ----------------------------------------------------------------------
def process_folder(folder: Path, level_name=None, unite_obj=None, chapter_obj=None,
                   auto_create=False, user=None, results=None):
    """
    Recursively process a folder.
    - level_name: the level string (if known)
    - unite_obj: a Unite instance (if already determined)
    - chapter_obj: a Chapter instance (if already determined)
    """
    if results is None:
        results = {'mcq':0, 'qa':0, 'tf':0, 'flash':0, 'term':0, 'summary':0, 'clinical':0,
                   'errors':[]}

    # CASE 1: We already have a Chapter → process files directly
    if chapter_obj is not None:
        _process_chapter_files(folder, chapter_obj, user, results)
        return results

    # CASE 2: We have a Unite but no Chapter → look for chapter subfolders
    if unite_obj is not None:
        for item in folder.iterdir():
            if item.is_dir():
                chapter_candidate = item.name
                norm_chapter = normalize_french(chapter_candidate)
                # Find or create Chapter under this Unite
                chapter = Chapter.objects.filter(ue=unite_obj, title__iexact=norm_chapter).first()
                if not chapter and auto_create:
                    # Create a basic chapter (you may want to add more fields)
                    chapter = Chapter.objects.create(
                        ue=unite_obj,
                        title=chapter_candidate,
                    )
                if chapter:
                    process_folder(item, level_name, unite_obj, chapter, auto_create, user, results)
                else:
                    results['errors'].append(f"Ignoré (chapitre inconnu) : {item}")
        return results

    # CASE 3: We have a level name but no Unite → look for unite subfolders
    if level_name is not None:
        for item in folder.iterdir():
            if item.is_dir():
                unite_candidate = item.name
                norm_unite = normalize_french(unite_candidate)
                # Find Unite with this level and title
                unite = Unite.objects.filter(level__iexact=normalize_french(level_name),
                                             title__iexact=norm_unite).first()
                if not unite and auto_create:
                    unite = Unite.objects.create(
                        level=level_name,
                        title=unite_candidate,
                        description=f"Créé automatiquement depuis {folder}"
                    )
                if unite:
                    process_folder(item, level_name, unite, None, auto_create, user, results)
                else:
                    results['errors'].append(f"Ignoré (UE inconnue) : {item}")
        return results

    # CASE 4: No context yet – determine starting point
    # First, check if this folder itself contains data files (i.e., it's a chapter folder)
    if _has_data_files(folder):
        # We need to extract level, unite, chapter from the path
        # Expected: .../level/unite/chapter/
        parts = folder.parts
        if len(parts) >= 3:
            level_candidate = parts[-3]
            unite_candidate = parts[-2]
            chapter_candidate = parts[-1]
        elif len(parts) == 2:
            # Only two levels: maybe unite/chapter? But we need level.
            # Fallback: try to find unite by name and get its level from DB
            level_candidate = None
            unite_candidate = parts[-2]
            chapter_candidate = parts[-1]
        else:
            results['errors'].append(f"Chemin trop court pour déterminer le contexte : {folder}")
            return results

        # Find Unite
        unite = None
        if level_candidate:
            norm_level = normalize_french(level_candidate)
            norm_unite = normalize_french(unite_candidate)
            unite = Unite.objects.filter(level__iexact=norm_level, title__iexact=norm_unite).first()
            if not unite and auto_create:
                unite = Unite.objects.create(level=level_candidate, title=unite_candidate)
        else:
            # No level in path – try to find unite by title only (may be ambiguous)
            norm_unite = normalize_french(unite_candidate)
            unites = list(Unite.objects.filter(title__iexact=norm_unite))
            if len(unites) == 1:
                unite = unites[0]
            elif len(unites) > 1:
                results['errors'].append(f"Plusieurs UE nommées '{unite_candidate}' existent. Précisez le niveau.")
                return results
            # else none – will be handled below

        if not unite:
            results['errors'].append(f"UE '{unite_candidate}' introuvable (et création automatique désactivée ou impossible).")
            return results

        # Find Chapter
        norm_chapter = normalize_french(chapter_candidate)
        chapter = Chapter.objects.filter(ue=unite, title__iexact=norm_chapter).first()
        if not chapter and auto_create:
            chapter = Chapter.objects.create(ue=unite, title=chapter_candidate, created_by=user)
        if not chapter:
            results['errors'].append(f"Chapitre '{chapter_candidate}' introuvable sous UE '{unite.title}'.")
            return results

        # Now process files in this chapter folder
        _process_chapter_files(folder, chapter, user, results)
        return results

    # CASE 5: No data files – this folder is either a level or a unite folder
    # Try to interpret as a unite folder first: check if folder name matches any Unite
    folder_name = folder.name
    norm_name = normalize_french(folder_name)
    unites_with_this_title = list(Unite.objects.filter(title__iexact=norm_name))

    if len(unites_with_this_title) == 1:
        # It's a unite folder – use that unite (level is known from the unite record)
        unite = unites_with_this_title[0]
        level_name = unite.level  # actual level string from DB
        # Now process its subfolders as chapters
        for item in folder.iterdir():
            if item.is_dir():
                chapter_candidate = item.name
                norm_chapter = normalize_french(chapter_candidate)
                chapter = Chapter.objects.filter(ue=unite, title__iexact=norm_chapter).first()
                if not chapter and auto_create:
                    chapter = Chapter.objects.create(ue=unite, title=chapter_candidate, created_by=user)
                if chapter:
                    process_folder(item, level_name, unite, chapter, auto_create, user, results)
                else:
                    results['errors'].append(f"Ignoré (chapitre inconnu) : {item}")
        return results

    elif len(unites_with_this_title) > 1:
        # Ambiguous – we need the level from parent folder
        parent = folder.parent
        if parent == folder:  # no parent
            results['errors'].append(f"Plusieurs UE nommées '{folder_name}'. Utilisez le chemin complet incluant le niveau.")
            return results
        level_candidate = parent.name
        norm_level = normalize_french(level_candidate)
        # Find the specific Unite
        unite = Unite.objects.filter(level__iexact=norm_level, title__iexact=norm_name).first()
        if not unite:
            results['errors'].append(f"UE '{folder_name}' avec niveau '{level_candidate}' introuvable.")
            return results
        # Now proceed as unite folder with known level
        for item in folder.iterdir():
            if item.is_dir():
                # ... same as above
                chapter_candidate = item.name
                norm_chapter = normalize_french(chapter_candidate)
                chapter = Chapter.objects.filter(ue=unite, title__iexact=norm_chapter).first()
                if not chapter and auto_create:
                    chapter = Chapter.objects.create(ue=unite, title=chapter_candidate, created_by=user)
                if chapter:
                    process_folder(item, level_candidate, unite, chapter, auto_create, user, results)
                else:
                    results['errors'].append(f"Ignoré (chapitre inconnu) : {item}")
        return results

    else:
        # No Unite with this title – treat folder as a level folder
        level_name = folder_name
        # Look for unite subfolders
        for item in folder.iterdir():
            if item.is_dir():
                unite_candidate = item.name
                norm_unite = normalize_french(unite_candidate)
                unite = Unite.objects.filter(level__iexact=normalize_french(level_name),
                                             title__iexact=norm_unite).first()
                if not unite and auto_create:
                    unite = Unite.objects.create(level=level_name, title=unite_candidate)
                if unite:
                    process_folder(item, level_name, unite, None, auto_create, user, results)
                else:
                    results['errors'].append(f"Ignoré (UE inconnue) : {item}")
        return results


def _has_data_files(folder):
    """Check if folder contains any file with a known pattern."""
    for f in folder.iterdir():
        if f.is_file():
            name = f.name.lower()
            if (name.endswith('.csv') and any(k in name for k in ['mcq','qcm','qa','tf','truefalse','flash','flashcard','term','terminology'])) \
               or (name.endswith('.txt') and any(k in name for k in ['summary','clinical','cas'])):
                return True
    return False


def _process_chapter_files(folder, chapter, user, results):
    """Import all recognized files in a chapter folder."""
    for file_path in folder.iterdir():
        if not file_path.is_file():
            continue
        fname = file_path.name.lower()
        try:
            if fname.endswith('.csv'):
                if 'mcq' in fname or 'qcm' in fname:
                    cnt, errs = process_mcq_file(file_path, chapter, user)
                    results['mcq'] += cnt
                    results['errors'].extend(errs)
                elif 'qa' in fname:
                    cnt, errs = process_qa_file(file_path, chapter, user)
                    results['qa'] += cnt
                    results['errors'].extend(errs)
                elif 'tf' in fname or 'truefalse' in fname:
                    cnt, errs = process_tf_file(file_path, chapter, user)
                    results['tf'] += cnt
                    results['errors'].extend(errs)
                elif 'flash' in fname or 'flashcard' in fname:
                    cnt, errs = process_flashcard_file(file_path, chapter, user)
                    results['flash'] += cnt
                    results['errors'].extend(errs)
            elif fname.endswith('.txt'):
                if 'summary' in fname:
                    cnt, errs = process_summary_file(file_path, chapter, user)
                    results['summary'] += cnt
                    results['errors'].extend(errs)


                # elif 'clinical' in fname or 'cas' in fname:
                #     cnt, errs = process_clinical_case_file(file_path, chapter, user)
                #     results['clinical'] += cnt
                #     results['errors'].extend(errs)

                
        except Exception as e:
            results['errors'].append(f"Erreur fichier {file_path.name}: {str(e)}")


@login_required
def bulk_import_chapter_data(request):
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission.")
        return redirect('lecon:subject_list')

    if request.method == 'POST':
        form = ChapterDataFolderImportForm(request.POST)
        if form.is_valid():
            folder_path = form.cleaned_data['folder_path'].strip()
            auto_create = form.cleaned_data['auto_create_missing']
            root = Path(folder_path).resolve()

            if not root.is_dir():
                messages.error(request, f"Le dossier n'existe pas : {root}")
                return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})

            # Initialize results
            results = {
                'mcq': 0, 'qa': 0, 'tf': 0,
                'flashcard': 0, 'terminology': 0,
                'summary': 0, 'clinical case': 0,
                'errors': []
            }

            # Start recursive processing
            process_folder(root, auto_create=auto_create, user=request.user, results=results)

            # Build summary messages
            total_success = sum(results[k] for k in ['mcq','qa','tf','flashcard','terminology','summary'])
            total_errors = len(results['errors'])

            if total_success > 0:
                messages.success(request, f"Import terminé : {total_success} éléments créés.")
            if total_errors > 0:
                messages.warning(request, f"{total_errors} erreurs rencontrées.")
                for err in results['errors'][:10]:
                    messages.error(request, err)
                if total_errors > 10:
                    messages.error(request, f"... et {total_errors-10} autres erreurs.")

            return render(request, 'lessoncopy/bulk_import_folder_path.html', {
                'form': form,
                'results': results
            })
    else:
        form = ChapterDataFolderImportForm()

    return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})







# REUSE WHEN CLINICAL CASE IS IMPLEMENTED


# def process_clinical_case_file(file_path, chapter, user):
#     """Import ClinicalCase from plain text file."""
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             content = f.read()
#         # You might want to extract a title from the first line or filename
#         title = Path(file_path).stem.replace('_', ' ').title()
#         ClinicalCase.objects.create(
#             chapter=chapter,
#             title=title,
#             description=content,
#             created_by=user
#         )
#         return 1, []
#     except Exception as e:
#         return 0, [f"Erreur lecture cas clinique: {str(e)}"]


# ---------- Main view ----------
# @login_required
# def bulk_import_chapter_data(request):
#     if not request.user.is_staff:
#         messages.error(request, "Vous n'avez pas la permission.")
#         return redirect('lecon:subject_list')

#     if request.method == 'POST':
#         form = ChapterDataFolderImportForm(request.POST)
#         if form.is_valid():
#             folder_path = form.cleaned_data['folder_path'].strip()
#             auto_create = form.cleaned_data['auto_create_missing']
#             chapter_folder = Path(folder_path).resolve()

#             if not chapter_folder.is_dir():
#                 messages.error(request, f"Le dossier n'existe pas : {chapter_folder}")
#                 return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})

#             # ----- Parse path to get level, unite, chapter names -----
#             # Expected: .../level/unite/chapter/
#             parts = chapter_folder.parts
#             if len(parts) < 3:
#                 messages.error(request, "Le chemin doit contenir au moins trois niveaux : .../niveau/ue/chapitre/")
#                 return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})

#             level_name = parts[-3]
#             unite_name = parts[-2]
#             chapter_name = parts[-1]

#             norm_level = normalize_french(level_name)
#             norm_unite = normalize_french(unite_name)
#             norm_chapter = normalize_french(chapter_name)

#             # ----- Find or create Unite -----
#             unite = Unite.objects.filter(level__iexact=norm_level, title__iexact=norm_unite).first()
#             if not unite:
#                 if auto_create:
#                     unite = Unite.objects.create(
#                         level=level_name,  # keep original case
#                         title=unite_name,
#                         description=f"Créé automatiquement depuis {chapter_folder}"
#                     )
#                 else:
#                     messages.error(request, f"UE '{unite_name}' avec niveau '{level_name}' introuvable.")
#                     return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})

#             # ----- Find or create Chapter -----
#             chapter = Chapter.objects.filter(ue=unite, title__iexact=norm_chapter).first()
#             if not chapter:
#                 if auto_create:
#                     # You may need to set sensible defaults for other fields
#                     chapter = Chapter.objects.create(
#                         ue=unite,
#                         title=chapter_name,
#                         chapter_number=1,  # adjust logic if needed
#                         content="",
#                         created_by=request.user
#                     )
#                 else:
#                     messages.error(request, f"Chapitre '{chapter_name}' introuvable dans l'UE '{unite.title}'.")
#                     return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})

#             # ----- Process all files in the chapter folder -----
#             results = {
#                 'mcq': {'success': 0, 'errors': []},
#                 'qa': {'success': 0, 'errors': []},
#                 'tf': {'success': 0, 'errors': []},
#                 'flash': {'success': 0, 'errors': []},
#                 'term': {'success': 0, 'errors': []},
#                 'summary': {'success': 0, 'errors': []},
#                 'clinical': {'success': 0, 'errors': []},
#             }

#             for file_path in chapter_folder.iterdir():
#                 if not file_path.is_file():
#                     continue
#                 fname = file_path.name.lower()

#                 # Detect type from filename
#                 if fname.endswith('.csv'):
#                     if 'mcq' in fname or 'qcm' in fname:
#                         cnt, errs = process_mcq_file(file_path, chapter, request.user)
#                         results['mcq']['success'] += cnt
#                         results['mcq']['errors'].extend(errs)
#                     elif 'qa' in fname:
#                         cnt, errs = process_qa_file(file_path, chapter, request.user)
#                         results['qa']['success'] += cnt
#                         results['qa']['errors'].extend(errs)
#                     elif 'tf' in fname or 'truefalse' in fname:
#                         cnt, errs = process_tf_file(file_path, chapter, request.user)
#                         results['tf']['success'] += cnt
#                         results['tf']['errors'].extend(errs)
#                     elif 'flash' in fname:
#                         cnt, errs = process_flashcard_file(file_path, chapter, request.user)
#                         results['flash']['success'] += cnt
#                         results['flash']['errors'].extend(errs)
#                     elif 'term' in fname:
#                         cnt, errs = process_terminology_file(file_path, chapter, request.user)
#                         results['term']['success'] += cnt
#                         results['term']['errors'].extend(errs)
#                 elif fname.endswith('.txt'):
#                     if 'summary' in fname:
#                         cnt, errs = process_summary_file(file_path, chapter, request.user)
#                         results['summary']['success'] += cnt
#                         results['summary']['errors'].extend(errs)


#                     # elif 'clinical' in fname or 'cas' in fname:
#                     #     cnt, errs = process_clinical_case_file(file_path, chapter, request.user)
#                     #     results['clinical']['success'] += cnt
#                     #     results['clinical']['errors'].extend(errs)

#             # ----- Build summary messages -----
#             total_success = sum(v['success'] for v in results.values())
#             total_errors = sum(len(v['errors']) for v in results.values())

#             if total_success > 0:
#                 messages.success(request, f"Import terminé : {total_success} éléments créés.")
#             if total_errors > 0:
#                 for key, data in results.items():
#                     if data['errors']:
#                         messages.warning(request, f"{key.upper()} : {len(data['errors'])} erreurs")
#                         # Show first few
#                         for err in data['errors'][:3]:
#                             messages.error(request, f"  {err}")
#                         if len(data['errors']) > 3:
#                             messages.error(request, f"  ... et {len(data['errors'])-3} autres")

#             return render(request, 'lessoncopy/bulk_import_folder_path.html', {
#                 'form': form,
#                 'results': results,
#                 'chapter': chapter
#             })
#     else:
#         form = ChapterDataFolderImportForm()

#     return render(request, 'lessoncopy/bulk_import_folder_path.html', {'form': form})
