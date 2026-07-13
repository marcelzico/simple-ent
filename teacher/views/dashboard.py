from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
import json
from ..decorators import teacher_required
from ..utils import TeacherStats
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, QAResult, TrueFalseResult
# from clinical_case_simple.models import Enoncé
# from quizlet_copy.models import FlashcardSet
from teacher.models import TeacherDashboardWidget
from student.models import StudentProfile


@login_required
@teacher_required
def dashboard_view(request):
    """
    Vue principale du tableau de bord enseignant
    """
    teacher = request.user
    
    # Récupérer les préférences des widgets
    widgets_config = TeacherDashboardWidget.objects.filter(
        teacher=teacher,
        is_visible=True
    ).order_by('order')
    
    # Récupérer les unités enseignées
    teaching_unites = Unite.objects.filter(teachers=teacher)
    unite_id = request.GET.get('unite')
    
    selected_unite = None
    if unite_id and teaching_unites.filter(id=unite_id).exists():
        selected_unite = Unite.objects.get(id=unite_id)
    
    # Initialiser les statistiques
    stats = TeacherStats(teacher, selected_unite)
    
    # Récupérer les étudiants par niveau (pour affichage)
    students_by_level = stats.get_students_count_by_level()
    
    # Statistiques détaillées
    context = {
        'teacher': teacher,
        'teaching_unites': teaching_unites,
        'selected_unite': selected_unite,
        'widgets_config': widgets_config,
        
        # Statistiques générales
        'unites_count': teaching_unites.count(),
        'students_count': stats.get_students_count(),
        'students_by_level': students_by_level,
        'mcq_count': stats.get_mcq_count(),
        'qa_count': stats.get_qa_count(),
        'tf_count': stats.get_tf_count(),
        # 'flashcard_sets_count': FlashcardSet.objects.filter(
        #     created_by=teacher
        # ).count(),
        # 'clinical_cases_count': Enoncé.objects.filter(
        #     auteur=teacher
        # ).count(),
        
        # Scores moyens
        'avg_mcq_score': stats.get_average_mcq_score(),
        'avg_qa_score': stats.get_average_qa_score(),
        'avg_tf_score': stats.get_average_tf_score(),
        'global_avg_score': (
            stats.get_average_mcq_score() + 
            stats.get_average_qa_score() + 
            stats.get_average_tf_score()
        ) / 3 if stats.get_average_mcq_score() > 0 else 0,
        
        # Taux de complétion
        'completion_rate': stats.get_chapter_completion_rate(),
        
        # Distribution des scores (pour graphique)
        'score_distribution': stats.get_score_distribution(),
        
        # Top et bottom étudiants
        'top_students': stats.get_top_students(5),
        'struggling_students': stats.get_struggling_students(5, 50),
        
        # Activité récente
        'recent_activity': stats.get_recent_activity(7),
        
        # Données pour graphiques
        'weekly_performance': _get_weekly_performance(teacher, selected_unite),
        'chapter_completion_data': _get_chapter_completion_data(teacher, selected_unite),
    }
    
    return render(request, 'teacher/dashboard/index.html', context)


def _get_weekly_performance(teacher, unite=None):
    """
    Récupère les performances des 7 derniers jours
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)
    
    # Récupérer les étudiants concernés
    if unite:
        levels = [unite.level] if unite.level else []
    else:
        unites = Unite.objects.filter(teachers=teacher)
        levels = [u.level for u in unites if u.level]
    
    if not levels:
        return {
            'days': json.dumps([]),
            'mcq': json.dumps([]),
            'qa': json.dumps([]),
            'tf': json.dumps([]),
        }
    
    # Récupérer les étudiants des niveaux concernés
    students = StudentProfile.objects.filter(
        level__in=levels,
        user__is_student=True,
        is_active_student=True
    ).values_list('user_id', flat=True)
    
    days = []
    mcq_scores = []
    qa_scores = []
    tf_scores = []
    
    for i in range(7):
        day_start = (end_date - timedelta(days=6-i)).replace(hour=0, minute=0, second=0)
        day_end = day_start + timedelta(days=1)
        days.append(day_start.strftime('%d/%m'))
        
        # Scores MCQ du jour
        mcq_day = MCQResult.objects.filter(
            student_id__in=students,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(avg=Avg('score'))['avg'] or 0
        mcq_scores.append(round(mcq_day, 1))
        
        # Scores QA du jour
        qa_day = QAResult.objects.filter(
            student_id__in=students,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(avg=Avg('score'))['avg'] or 0
        qa_scores.append(round(qa_day, 1))
        
        # Scores TF du jour
        tf_day = TrueFalseResult.objects.filter(
            student_id__in=students,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).aggregate(avg=Avg('score'))['avg'] or 0
        tf_scores.append(round(tf_day, 1))
    
    return {
        'days': json.dumps(days),
        'mcq': json.dumps(mcq_scores),
        'qa': json.dumps(qa_scores),
        'tf': json.dumps(tf_scores),
    }


def _get_chapter_completion_data(teacher, unite=None):
    """
    Récupère les données de complétion par chapitre
    """
    if unite:
        unites = [unite]
        levels = [unite.level] if unite.level else []
    else:
        unites = Unite.objects.filter(teachers=teacher)
        levels = [u.level for u in unites if u.level]
    
    if not levels:
        return {
            'chapters': json.dumps([]),
            'rates': json.dumps([]),
        }
    
    # Récupérer les étudiants des niveaux concernés
    students = StudentProfile.objects.filter(
        level__in=levels,
        user__is_student=True,
        is_active_student=True
    )
    total_students = students.count()
    
    chapter_names = []
    completion_rates = []
    
    for unite_obj in unites:
        chapters = Chapter.objects.filter(ue=unite_obj, is_active=True)
        
        for chapter in chapters:
            # Compter les étudiants qui ont au moins une tentative sur ce chapitre
            students_with_activity = set()
            
            for result_model in [MCQResult, QAResult, TrueFalseResult]:
                for user_id in result_model.objects.filter(
                    chapter=chapter,
                    student__student_profile__level__in=levels
                ).values_list('student_id', flat=True).distinct():
                    students_with_activity.add(user_id)
            
            rate = (len(students_with_activity) / total_students) * 100 if total_students > 0 else 0
            
            chapter_names.append(f"{unite_obj.title[:15]} - {chapter.title[:25]}")
            completion_rates.append(round(rate, 1))
    
    return {
        'chapters': json.dumps(chapter_names[:10]),  # Limiter à 10 pour lisibilité
        'rates': json.dumps(completion_rates[:10]),
    }

