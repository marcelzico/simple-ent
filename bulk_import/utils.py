import os
import re
import unicodedata
from pathlib import Path
from django.conf import settings
import logging
logger = logging.getLogger(__name__)


def normalize_french(text):
    if not text:
        return ''
    nfkd = unicodedata.normalize('NFKD', text)
    without_accents = ''.join(c for c in nfkd if not unicodedata.combining(c))
    lowered = without_accents.lower()
    lowered = lowered.replace('œ', 'oe').replace('æ', 'ae')
    return lowered.strip()


def clean_filename_for_title(filename):
    """Remove leading digits and extension."""
    base = os.path.splitext(filename)[0]
    base = re.sub(r'^\d+_', '', base)
    return base.strip()


def get_chapter_title_from_filename(filename):
    base = os.path.splitext(filename)[0]
    # Remove version suffixes: _v1, -02, (01), [v2], etc.
    base = re.sub(r'[_-]?\(?\d+\)?$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'[_-]?v\d+$', '', base, flags=re.IGNORECASE)
    return base.strip()


def get_shifted_files_for_chapter(level, unite_title, chapter_title):
    base = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_SHIFTED_DIR / level / unite_title
    logger.info(f"Searching for shifted files in: {base}")
    if not base.exists():
        logger.warning(f"Path does not exist: {base}")
        return []
    files = []
    norm_chapter = normalize_french(chapter_title)
    for f in base.glob('*.docx'):
        file_title = get_chapter_title_from_filename(f.name)
        if normalize_french(file_title) == norm_chapter:
            files.append(f)
    logger.info(f"Found {len(files)} matching files for chapter '{chapter_title}'")
    return files


def get_level_folders():
    splitted = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_SPLITTED_DIR
    if not splitted.exists():
        return []
    return [d.name for d in splitted.iterdir() if d.is_dir()]


def get_unite_folders(level):
    path = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_SPLITTED_DIR / level
    if not path.exists():
        return []
    return [d.name for d in path.iterdir() if d.is_dir()]


def get_chapter_files_for_unite(level, unite_title, subdir='splitted'):
    base = Path(settings.BULK_IMPORT_ROOT) / subdir / level / unite_title
    if not base.exists():
        return []
    return [f for f in base.glob('*.docx') if f.is_file()]


def get_exercise_files_for_chapter(level, unite_title, chapter_title):
    base = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_EXERCICES_DIR / level / unite_title / chapter_title
    if not base.exists():
        return {}
    files = {}
    for f in base.iterdir():
        if not f.is_file():
            continue
        name_lower = f.name.lower()
        if name_lower.endswith('.csv'):
            if 'mcq' in name_lower or 'qcm' in name_lower:
                files['mcq'] = f
            elif 'qa' in name_lower:
                files['qa'] = f
            elif 'tf' in name_lower or 'truefalse' in name_lower:
                files['tf'] = f
            elif 'flash' in name_lower:
                files['flashcard'] = f
            elif 'term' in name_lower:
                files['terminology'] = f
        elif name_lower.endswith('.txt'):
            if 'summary' in name_lower:
                files['summary'] = f
            elif 'clinical' in name_lower or 'cas' in name_lower:
                files['clinical'] = f
    return files


def get_folder_stats():
    """Return statistics for the four main import folders."""
    root = Path(settings.BULK_IMPORT_ROOT)
    stats = {
        'splitted': {'levels': [], 'unite_count': 0, 'chapter_files': 0, 'total_files': 0},
        'exercices': {'levels': [], 'unite_count': 0, 'chapter_folders': 0, 'files_by_type': {}, 'total_files': 0},
        'shifted_down': {'levels': [], 'unite_count': 0, 'chapter_files': 0, 'total_files': 0},
        'original': {'levels': [], 'unite_count': 0, 'docx_files': 0, 'total_files': 0},
    }

    # Helper to count files with given extensions
    def count_files(path, extensions=None):
        if not path.exists():
            return 0
        if extensions:
            return sum(1 for f in path.iterdir() if f.is_file() and f.suffix.lower() in extensions)
        return sum(1 for f in path.iterdir() if f.is_file())

    # --- splitted ---
    splitted = root / settings.BULK_SPLITTED_DIR
    if splitted.exists():
        for level_dir in splitted.iterdir():
            if level_dir.is_dir():
                stats['splitted']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['splitted']['unite_count'] += 1
                        # count .docx files in this unite
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['splitted']['chapter_files'] += docx_count
                        stats['splitted']['total_files'] += docx_count

    # --- exercices ---
    exercices = root / settings.BULK_EXERCICES_DIR
    file_type_map = {
        'mcq': ['.csv'],
        'qa': ['.csv'],
        'tf': ['.csv'],
        'flashcard': ['.csv'],
        'terminology': ['.csv'],
        'summary': ['.txt'],
        'clinical': ['.txt'],
    }
    if exercices.exists():
        for level_dir in exercices.iterdir():
            if level_dir.is_dir():
                stats['exercices']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['exercices']['unite_count'] += 1
                        for chapter_dir in unite_dir.iterdir():
                            if chapter_dir.is_dir():
                                stats['exercices']['chapter_folders'] += 1
                                # classify files
                                for file in chapter_dir.iterdir():
                                    if file.is_file():
                                        ext = file.suffix.lower()
                                        name = file.name.lower()
                                        stats['exercices']['total_files'] += 1
                                        # determine type
                                        for ftype, exts in file_type_map.items():
                                            if ext in exts:
                                                # additional check for keywords
                                                if ftype == 'mcq' and ('mcq' in name or 'qcm' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'qa' and 'qa' in name:
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'tf' and ('tf' in name or 'truefalse' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'flashcard' and ('flash' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'terminology' and ('term' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'summary' and ('summary' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                elif ftype == 'clinical' and ('clinical' in name or 'cas' in name):
                                                    stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                break  # matched, exit loop
                                        else:
                                            # unknown file type
                                            stats['exercices']['files_by_type']['other'] = stats['exercices']['files_by_type'].get('other', 0) + 1

    # --- shifted down ---
    shifted = root / settings.BULK_SHIFTED_DIR
    if shifted.exists():
        for level_dir in shifted.iterdir():
            if level_dir.is_dir():
                stats['shifted_down']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['shifted_down']['unite_count'] += 1
                        # count .docx files in this unite (could be multiple versions)
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['shifted_down']['chapter_files'] += docx_count
                        stats['shifted_down']['total_files'] += docx_count

    # --- original ---
    original = root / 'original'   # note: not in settings, but fixed name as per user's description
    if original.exists():
        for level_dir in original.iterdir():
            if level_dir.is_dir():
                stats['original']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['original']['unite_count'] += 1
                        # count any .docx files directly in unite (or deeper? user said we ignore deeper for now)
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['original']['docx_files'] += docx_count
                        stats['original']['total_files'] += docx_count
                        # also count other files if any
                        other_count = sum(1 for f in unite_dir.iterdir() if f.is_file() and f.suffix.lower() not in {'.docx'})
                        stats['original']['total_files'] += other_count

    return stats

