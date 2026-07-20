import os
import re
import unicodedata
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def normalize_french(text):
    """Normalize text for comparison: lowercase, remove accents, strip."""
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
    base = re.sub(r'[_-]?(v?\d+)?$', '', base, flags=re.IGNORECASE)
    base = re.sub(r'[_-]?v\d+$', '', base, flags=re.IGNORECASE)
    return base.strip()

def _find_folder_robust(parent_path, folder_name):
    """Find a folder by name, robust to case and accent differences."""
    if not parent_path.exists():
        return None
    
    # Try exact match first (fastest)
    exact = parent_path / folder_name
    if exact.exists() and exact.is_dir():
        return exact
    
    # Fallback: normalized matching
    norm_target = normalize_french(folder_name)
    for d in parent_path.iterdir():
        if d.is_dir() and normalize_french(d.name) == norm_target:
            return d
    
    return None

def get_shifted_files_for_chapter(level, unite_title, chapter_title):
    """Get shifted .docx files for a chapter (robust to folder name variations)."""
    root = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_SHIFTED_DIR
    
    # Robustly find level folder
    level_folder = _find_folder_robust(root, level)
    if not level_folder:
        logger.warning(f"Level folder not found: {level}")
        return []
    
    # Robustly find unite folder
    unite_folder = _find_folder_robust(level_folder, unite_title)
    if not unite_folder:
        logger.warning(f"Unite folder not found: {unite_title} in {level_folder}")
        return []
    
    files = []
    norm_chapter = normalize_french(chapter_title)
    
    for f in unite_folder.glob('*.docx'):
        file_title = get_chapter_title_from_filename(f.name)
        if normalize_french(file_title) == norm_chapter:
            files.append(f)
    
    logger.info(f"Found {len(files)} shifted files for chapter '{chapter_title}'")
    return files

def get_exercise_folder_for_chapter(level, unite_title, chapter_title):
    """Find the exercise folder for a chapter (robust to all folder name variations)."""
    root = Path(settings.BULK_IMPORT_ROOT) / settings.BULK_EXERCICES_DIR
    
    # Robustly find level folder
    level_folder = _find_folder_robust(root, level)
    if not level_folder:
        logger.warning(f"Exercices: Level folder not found: {level}")
        return None
    
    # Robustly find unite folder
    unite_folder = _find_folder_robust(level_folder, unite_title)
    if not unite_folder:
        logger.warning(f"Exercices: Unite folder not found: {unite_title} in {level_folder}")
        return None
    
    # Robustly find chapter folder
    chapter_folder = _find_folder_robust(unite_folder, chapter_title)
    if not chapter_folder:
        logger.warning(f"Exercices: Chapter folder not found: {chapter_title} in {unite_folder}")
        return None
    
    return chapter_folder

def get_exercise_files_for_chapter(level, unite_title, chapter_title):
    """Get exercise files for a chapter using robust folder finding and prefix-based type detection."""
    chapter_folder = get_exercise_folder_for_chapter(level, unite_title, chapter_title)
    if not chapter_folder:
        logger.error(f"Could not find exercise folder for {level}/{unite_title}/{chapter_title}")
        return {}
    
    logger.info(f"Found exercise folder: {chapter_folder}")
    
    files = {}
    for f in chapter_folder.iterdir():
        if not f.is_file():
            continue
        
        name_lower = f.name.lower()
        
        # Use PREFIX matching for reliable file type detection
        if name_lower.endswith('.csv'):
            if name_lower.startswith('mcq-') or name_lower.startswith('qcm-'):
                files['mcq'] = f
            elif name_lower.startswith('qa-'):
                files['qa'] = f
            elif name_lower.startswith('tf-') or name_lower.startswith('truefalse-'):
                files['tf'] = f
            elif name_lower.startswith('flashcard-') or name_lower.startswith('flash-'):
                files['flashcard'] = f
            elif name_lower.startswith('terminology-') or name_lower.startswith('term-'):
                files['terminology'] = f
            else:
                logger.warning(f"Unknown CSV file type: {f.name}")
        
        elif name_lower.endswith('.txt'):
            if name_lower.startswith('summary-') or name_lower.startswith('resume-'):
                files['summary'] = f
            elif name_lower.startswith('clinical_case-') or name_lower.startswith('clinical-') or name_lower.startswith('cas-'):
                files['clinical'] = f
            else:
                logger.warning(f"Unknown TXT file type: {f.name}")
    
    logger.info(f"Found {len(files)} exercise files: {list(files.keys())}")
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

def get_folder_stats():
    """Return statistics for the four main import folders."""
    root = Path(settings.BULK_IMPORT_ROOT)
    stats = {
        'splitted': {'levels': [], 'unite_count': 0, 'chapter_files': 0, 'total_files': 0},
        'exercices': {'levels': [], 'unite_count': 0, 'chapter_folders': 0, 'files_by_type': {}, 'total_files': 0},
        'shifted_down': {'levels': [], 'unite_count': 0, 'chapter_files': 0, 'total_files': 0},
        'original': {'levels': [], 'unite_count': 0, 'docx_files': 0, 'total_files': 0},
    }
    
    def count_files(path, extensions=None):
        if not path.exists():
            return 0
        if extensions:
            return sum(1 for f in path.iterdir() if f.is_file() and f.suffix.lower() in extensions)
        return sum(1 for f in path.iterdir() if f.is_file())
    
    # splitted
    splitted = root / settings.BULK_SPLITTED_DIR
    if splitted.exists():
        for level_dir in splitted.iterdir():
            if level_dir.is_dir():
                stats['splitted']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['splitted']['unite_count'] += 1
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['splitted']['chapter_files'] += docx_count
                        stats['splitted']['total_files'] += docx_count
    
    # exercices
    exercices = root / settings.BULK_EXERCICES_DIR
    file_type_map = {
        'mcq': ['mcq-', 'qcm-'],
        'qa': ['qa-'],
        'tf': ['tf-', 'truefalse-'],
        'flashcard': ['flashcard-', 'flash-'],
        'terminology': ['terminology-', 'term-'],
        'summary': ['summary-', 'resume-'],
        'clinical': ['clinical_case-', 'clinical-', 'cas-'],
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
                                for file in chapter_dir.iterdir():
                                    if file.is_file():
                                        stats['exercices']['total_files'] += 1
                                        name_lower = file.name.lower()
                                        
                                        # Use prefix matching
                                        matched = False
                                        for ftype, prefixes in file_type_map.items():
                                            if any(name_lower.startswith(p) for p in prefixes):
                                                stats['exercices']['files_by_type'][ftype] = stats['exercices']['files_by_type'].get(ftype, 0) + 1
                                                matched = True
                                                break
                                        
                                        if not matched:
                                            stats['exercices']['files_by_type']['other'] = stats['exercices']['files_by_type'].get('other', 0) + 1
    
    # shifted_down
    shifted = root / settings.BULK_SHIFTED_DIR
    if shifted.exists():
        for level_dir in shifted.iterdir():
            if level_dir.is_dir():
                stats['shifted_down']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['shifted_down']['unite_count'] += 1
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['shifted_down']['chapter_files'] += docx_count
                        stats['shifted_down']['total_files'] += docx_count
    
    # original
    original = root / 'original'
    if original.exists():
        for level_dir in original.iterdir():
            if level_dir.is_dir():
                stats['original']['levels'].append(level_dir.name)
                for unite_dir in level_dir.iterdir():
                    if unite_dir.is_dir():
                        stats['original']['unite_count'] += 1
                        docx_count = count_files(unite_dir, {'.docx'})
                        stats['original']['docx_files'] += docx_count
                        stats['original']['total_files'] += docx_count
                        other_count = sum(1 for f in unite_dir.iterdir() if f.is_file() and f.suffix.lower() not in {'.docx'})
                        stats['original']['total_files'] += other_count
    
    return stats


