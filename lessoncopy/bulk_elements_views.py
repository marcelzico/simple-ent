# views.py (in your quizzes app)
import csv
import io
import os
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from lecon.models import Chapter
from .forms import BulkUploadForm
from quizzes.models import MCQ, QuestionAnswer, TrueFalseQuiz
from quizlet_copy.models import FlashcardSet, Flashcard

# Decorator from your existing code
from subscriptions.decorators import non_student_required

@login_required
@non_student_required
def bulk_upload_chapter(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id)
    user = request.user

    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = request.FILES.getlist('csv_files')
            if not files:
                messages.error(request, 'No files selected.')
                return redirect('bulk_upload_chapter', chapter_id=chapter.id)

            # Initialize counters and error collectors
            results = {
                'mcq': {'success': 0, 'errors': []},
                'qa': {'success': 0, 'errors': []},
                'tf': {'success': 0, 'errors': []},
                'flashcard': {'success': 0, 'errors': []},
                'terminology': {'success': 0, 'errors': []},
            }

            for uploaded_file in files:
                # Determine type from filename
                filename = uploaded_file.name.lower()
                file_type = None
                if 'mcq' in filename or 'qcm' in filename:
                    file_type = 'mcq'
                elif 'qa' in filename or 'question_answer' in filename:
                    file_type = 'qa'
                elif 'tf' in filename or 'truefalse' in filename:
                    file_type = 'tf'
                elif 'flash' in filename or 'flashcard' in filename:
                    file_type = 'flash'
                elif 'term' in filename or 'terminology' in filename:
                    file_type = 'term'
                else:
                    # Unknown type – add error but continue with other files
                    results.setdefault('unknown', []).append(
                        f"File '{uploaded_file.name}' could not be identified (no type keyword)."
                    )
                    continue

                # Process the file according to its type
                try:
                    if file_type == 'mcq':
                        count, errors = process_mcq_file(uploaded_file, chapter, user)
                    elif file_type == 'qa':
                        count, errors = process_qa_file(uploaded_file, chapter, user)
                    elif file_type == 'tf':
                        count, errors = process_tf_file(uploaded_file, chapter, user)
                    elif file_type == 'flash':
                        count, errors = process_flashcard_file(uploaded_file, chapter, user)
                    else:
                        continue  # should not happen

                    results[file_type]['success'] += count
                    results[file_type]['errors'].extend(errors)

                except Exception as e:
                    results[file_type]['errors'].append(
                        f"File '{uploaded_file.name}' caused unexpected error: {str(e)}"
                    )

            # Build final messages
            total_success = sum(v['success'] for v in results.values() if isinstance(v, dict))
            total_errors = sum(len(v['errors']) for v in results.values() if isinstance(v, dict))

            if total_success > 0:
                messages.success(request, f'Successfully imported {total_success} items.')
            if total_errors > 0:
                for ftype, data in results.items():
                    if isinstance(data, dict) and data['errors']:
                        messages.warning(
                            request,
                            f"{ftype.upper()} errors: {', '.join(data['errors'][:3])}"
                            + (f" and {len(data['errors'])-3} more" if len(data['errors']) > 3 else "")
                        )

            return redirect('lecon:chapter_detail',
                            subject_pk=chapter.ue.id,
                            chapter_pk=chapter.id)
    else:
        form = BulkUploadForm()

    return render(request, 'lessoncopy/bulk_upload.html', {
        'form': form,
        'chapter': chapter
    })


def process_mcq_file(uploaded_file, chapter, user):
    """Process an MCQ CSV file."""
    count = 0
    errors = []
    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)
        for row_num, row in enumerate(reader, start=2):  # row 1 is header
            try:
                MCQ.objects.create(
                    chapter=chapter,
                    created_by=user,
                    question=row.get('question', '').strip(),
                    option1=row.get('option1', '').strip(),
                    option2=row.get('option2', '').strip(),
                    option3=row.get('option3', '').strip() or None,
                    option4=row.get('option4', '').strip() or None,
                    correct_option=int(row.get('correct') or row.get('answer') or row.get('réponse') or 1),
                    explanation=row.get('explanation') or row.get('explication') or '',
                    time_limit=int(row.get('time_limit', 30)),
                )
                count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"File read error: {str(e)}")
    return count, errors


def process_qa_file(uploaded_file, chapter, user):
    """Process a Question-Answer CSV file."""
    count = 0
    errors = []
    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)
        for row_num, row in enumerate(reader, start=2):
            try:
                QuestionAnswer.objects.create(
                    chapter=chapter,
                    created_by=user,
                    question=row.get('question', '').strip(),
                    sample_answer=row.get('answer') or row.get('réponse') or row.get('sample_answer') or '',
                    explanation=row.get('explanation') or row.get('explication') or '',
                    time_limit=int(row.get('time_limit', 300)),
                )
                count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"File read error: {str(e)}")
    return count, errors


def process_tf_file(uploaded_file, chapter, user):
    """Process a True/False CSV file."""
    count = 0
    errors = []
    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)
        for row_num, row in enumerate(reader, start=2):
            try:
                answer_text = row.get('answer') or row.get('correct') or row.get('réponse') or ''
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
                errors.append(f"Row {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"File read error: {str(e)}")
    return count, errors


def process_flashcard_file(uploaded_file, chapter, user):
    """Process a Flashcard CSV file."""
    count = 0
    errors = []
    try:
        decoded = uploaded_file.read().decode('utf-8-sig')
        io_string = io.StringIO(decoded)
        reader = csv.DictReader(io_string)
        for row_num, row in enumerate(reader, start=2):
            try:
                set_title = row.get('set_title', '').strip()
                if not set_title:
                    errors.append(f"Row {row_num}: Missing 'set_title'")
                    continue

                # Assuming FlashcardSet.title is a CharField (not FK). If it's FK to Chapter, adjust.
                # Based on your model: FlashcardSet.title = models.ForeignKey(Chapter, ...)
                # Actually, in your models, FlashcardSet.title is a ForeignKey to Chapter.
                # So we need to get or create a set for this chapter. But you might want different sets per chapter.
                # Let's assume you want one set per chapter. So we use chapter as the set identifier.
                # However, your model allows multiple sets for a chapter? Probably yes, because title is FK, not unique.
                # We'll use set_title as a name for the set, but since title is FK, we need a separate name field.
                # Wait, your FlashcardSet model:
                # title = models.ForeignKey(Chapter, on_delete=models.CASCADE)
                # So title points to a Chapter, not a string. That means each set is tied to one chapter, and you cannot have multiple sets per chapter unless you have another field.
                # But in your FlashcardSet, there's no 'name' field; the __str__ returns str(self.title) which is the chapter.
                # So essentially each chapter can have only ONE flashcard set? That's limiting.
                # I'll assume you want to allow multiple sets per chapter, so we need a name field. But your current model doesn't have it.
                # For now, I'll create a set per chapter using the chapter FK and a hardcoded name.
                # Actually, let's create a set if not exists, and attach flashcards to it. Since title is FK, we can create multiple sets for same chapter because there's no unique constraint.
                # But we need a way to distinguish them. The set_title from CSV can be used as description or ignored.
                # I'll just create one set per chapter (first one found or created) for simplicity.
                flashcard_set, _ = FlashcardSet.objects.get_or_create(
                    title=chapter,
                    is_public=True,
                    defaults={'created_by': user, 'description': ''}
                )

                Flashcard.objects.create(
                    flashcard_set=flashcard_set,
                    term=row.get('term').strip(),
                    definition=row.get('definition') or row.get('meaning'),
                )
                count += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
    except Exception as e:
        errors.append(f"File read error: {str(e)}")
    return count, errors



