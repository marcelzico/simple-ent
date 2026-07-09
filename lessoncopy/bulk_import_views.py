# lessoncopy/bulk_import_views.py

import os
from pathlib import Path
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.conf import settings
from lecon.models import Unite, Chapter
from lessoncopy.models import Importer
from lessoncopy.utils import extract_docx_to_model
from .forms import FolderImportForm   # adjust import as needed


@login_required
def bulk_import_chapters_from_folder(request):
    """Import all .docx files from a folder hierarchy: [level/]subject/chapter.docx"""
    if not request.user.is_staff:
        messages.error(request, "Vous n'avez pas la permission d'effectuer cette action.")
        return redirect('lecon:subject_list')

    if request.method == 'POST':
        form = FolderImportForm(request.POST)
        if form.is_valid():
            folder_path = form.cleaned_data['folder_path'].strip()
            root = Path(folder_path).resolve()

            if not root.is_dir():
                messages.error(request, f"Le dossier n'existe pas ou n'est pas accessible : {root}")
                return render(request, 'lessoncopy/bulk_import_folder.html', {'form': form})

            # Find all .docx files recursively
            docx_files = list(root.rglob('*.docx'))
            total_files = len(docx_files)
            if total_files == 0:
                messages.warning(request, "Aucun fichier .docx trouvé dans le chemin indiqué.")
                return render(request, 'lessoncopy/bulk_import_folder.html', {'form': form})

            # Preload database objects for fast matching
            unites = list(Unite.objects.all())
            chapters = list(Chapter.objects.select_related('ue').all())

            # Build lookup dictionaries
            # Unite: (level_normalized, title_normalized) -> Unite
            unite_lookup = {}
            for u in unites:
                key = (u.level.lower().strip(), u.title.lower().strip())
                unite_lookup[key] = u

            # Chapter: (unite_id, title_normalized) -> Chapter
            chapter_lookup = {}
            for c in chapters:
                key = (c.ue_id, c.title.lower().strip())
                chapter_lookup[key] = c

            results = {
                'processed': 0,
                'skipped': 0,
                'errors': [],
                'success': []
            }

            for file_path in docx_files:
                rel_path = file_path.relative_to(root)
                parts = rel_path.parts
                filename = file_path.name
                chapter_name = file_path.stem

                # ----- Determine level and subject from folder structure -----
                # parts: e.g. ("subject", "file.docx")   -> root is level
                #        ("level", "subject", "file.docx") -> root is above level
                #        ("file.docx")                    -> root is subject
                level_candidate = None
                subject_candidate = None

                if len(parts) == 1:
                    # File directly in root → root folder is the subject
                    subject_candidate = root.name
                    level_candidate = None   # will try to find subject without level
                elif len(parts) == 2:
                    # File in a subfolder → first part is subject, root is level
                    subject_candidate = parts[0]
                    level_candidate = root.name
                elif len(parts) >= 3:
                    # Deeper nesting: first part = level, second = subject
                    level_candidate = parts[0]
                    subject_candidate = parts[1]
                else:
                    # Should not happen
                    results['skipped'] += 1
                    results['errors'].append(f"{file_path} : structure de dossier inattendue")
                    continue

                # Normalize strings
                norm_subject = subject_candidate.lower().strip()
                norm_level = level_candidate.lower().strip() if level_candidate else None
                norm_chapter = chapter_name.lower().strip()

                # ----- Find the Unite -----
                found_unite = None
                if norm_level:
                    # Use level + subject
                    key = (norm_level, norm_subject)
                    found_unite = unite_lookup.get(key)
                    if not found_unite:
                        results['skipped'] += 1
                        results['errors'].append(
                            f"{file_path} : niveau '{level_candidate}' et matière '{subject_candidate}' introuvables"
                        )
                        continue
                else:
                    # No level provided – search subject by name only
                    candidates = [u for u in unites if u.title.lower().strip() == norm_subject]
                    if not candidates:
                        results['skipped'] += 1
                        results['errors'].append(
                            f"{file_path} : matière '{subject_candidate}' introuvable dans aucun niveau"
                        )
                        continue
                    elif len(candidates) > 1:
                        results['skipped'] += 1
                        results['errors'].append(
                            f"{file_path} : plusieurs matières nommées '{subject_candidate}' existent "
                            "(différents niveaux). Veuillez fournir le chemin complet incluant le niveau."
                        )
                        continue
                    else:
                        found_unite = candidates[0]

                # ----- Find the Chapter under this Unite -----
                chapter_key = (found_unite.id, norm_chapter)
                found_chapter = chapter_lookup.get(chapter_key)
                if not found_chapter:
                    results['skipped'] += 1
                    results['errors'].append(
                        f"{file_path} : chapitre '{chapter_name}' introuvable sous la matière '{found_unite.title}'"
                    )
                    continue

                # ----- Process the document -----
                importer = None
                try:
                    with transaction.atomic():
                        # Create Importer record
                        importer = Importer.objects.create(
                            chapter=found_chapter,
                            file_type='docx',
                            title=chapter_name,
                            processed=False
                        )

                        # Copy the file to Django's storage
                        from django.core.files import File
                        with open(file_path, 'rb') as f:
                            django_file = File(f)
                            importer.file.save(filename, django_file, save=True)

                        # Extract content into Copy objects
                        extract_docx_to_model(importer.file.path, found_chapter.id, importer)

                        # Mark as processed
                        importer.processed = True
                        importer.save()

                    results['processed'] += 1
                    results['success'].append(
                        f"{file_path} → {found_unite.title} - {found_chapter.title}"
                    )

                except Exception as e:
                    if importer and importer.id:
                        importer.delete()  # rollback the Importer record
                    results['errors'].append(
                        f"{file_path} : erreur lors du traitement – {str(e)}"
                    )

            # Summary messages
            msg = f"Traités : {results['processed']}  |  Ignorés : {results['skipped']}  |  Erreurs : {len(results['errors'])}"
            if results['processed'] > 0:
                messages.success(request, msg)
            else:
                messages.warning(request, msg)

            # Show first few errors
            for err in results['errors'][:5]:
                messages.error(request, err)
            if len(results['errors']) > 5:
                messages.error(request, f"... et {len(results['errors'])-5} autres erreurs.")

            return render(request, 'lessoncopy/bulk_import_folder.html', {
                'form': form,
                'results': results
            })

    else:
        form = FolderImportForm()

    return render(request, 'lessoncopy/bulk_import_folder.html', {'form': form})


