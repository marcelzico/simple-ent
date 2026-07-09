from django import template
from lessoncopy.models import StudySession

register = template.Library()

@register.filter
def get_section_study_time(chapters, user):
    """Calculate total study time for a section (list of chapters) for a user"""
    if not user.is_authenticated or not user.is_student:
        return 0
    
    total_seconds = 0
    for chapter in chapters:
        study_sessions = StudySession.objects.filter(
            user=user,
            chapter=chapter,
            completed=True
        )
        total_seconds += sum(session.duration_seconds for session in study_sessions)
    
    return total_seconds

@register.filter
def seconds_to_hours(seconds):
    """Convert seconds to hours"""
    return seconds // 3600

@register.filter
def seconds_to_minutes(seconds):
    """Convert seconds to remaining minutes"""
    return (seconds % 3600) // 60