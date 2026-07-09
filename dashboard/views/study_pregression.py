# dashboard/views.py
from django.shortcuts import render
from django.db.models import Count, Avg, Sum, Q, F, FloatField, Case, When, Value
from django.db.models.functions import TruncDate, ExtractWeekDay, Coalesce
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from utilisateur.models import User
from student.models import StudentProfile
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, TrueFalseResult, QAResult
from clinical_case_simple.models import ExamAttempt
from quizlet_copy.models import UserProgress
from lessoncopy.models import StudySession, UserAnnotation
from quizzes.models import MCQQuiz, QAQuiz
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json


class StudentProgressionDashboard:
    """Main dashboard class for student progression analytics"""
    
    def __init__(self, request):
        self.request = request
        self.student_filter = Q(is_student=True)
        
    def apply_filters(self, queryset, filter_data):
        """Apply filters to any queryset"""
        if filter_data.get('level'):
            queryset = queryset.filter(
                student_profile__level=filter_data['level']
            )
        if filter_data.get('unite'):
            queryset = queryset.filter(
                chapter__ue_id=filter_data['unite']
            )
        if filter_data.get('chapter'):
            queryset = queryset.filter(
                chapter_id=filter_data['chapter']
            )
        if filter_data.get('student'):
            queryset = queryset.filter(
                user_id=filter_data['student']
            )
        if filter_data.get('date_from'):
            queryset = queryset.filter(
                created_at__gte=filter_data['date_from']
            )
        if filter_data.get('date_to'):
            queryset = queryset.filter(
                created_at__lte=filter_data['date_to']
            )
        return queryset
    
    # ========== COMPONENT 1: GLOBAL KPIs ==========
    def get_global_kpis(self, filters=None):
        """Get KPI cards data"""
        # Base student queryset
        students = User.objects.filter(is_student=True)
        if filters and filters.get('level'):
            students = students.filter(student_profile__level=filters['level'])
        
        total_students = students.count()
        
        # Active students (have any study session in last 7 days)
        week_ago = timezone.now() - timedelta(days=7)
        active_students = students.filter(
            Q(studysession__start_time__gte=week_ago) |
            Q(mcqresult__created_at__gte=week_ago) |
            Q(truefalseresult__created_at__gte=week_ago)
        ).distinct().count()
        
        # Average quiz score across all types
        avg_mcq = MCQResult.objects.filter(student__is_student=True).aggregate(avg=Avg('score'))['avg'] or 0
        avg_tf = TrueFalseResult.objects.filter(student__is_student=True).aggregate(avg=Avg('score'))['avg'] or 0
        avg_qa = QAResult.objects.filter(student__is_student=True).aggregate(avg=Avg('score'))['avg'] or 0
        
        if filters:
            if filters.get('level'):
                avg_mcq = MCQResult.objects.filter(student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                avg_tf = TrueFalseResult.objects.filter(student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                avg_qa = QAResult.objects.filter(student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
        
        overall_avg = (avg_mcq + avg_tf + avg_qa) / 3 if (avg_mcq + avg_tf + avg_qa) > 0 else 0
        
        # At-risk students (average score < 50%)
        at_risk = 0
        for student in students:
            scores = []
            mcq_scores = MCQResult.objects.filter(student=student).values_list('score', flat=True)[:5]
            tf_scores = TrueFalseResult.objects.filter(student=student).values_list('score', flat=True)[:5]
            qa_scores = QAResult.objects.filter(student=student).values_list('score', flat=True)[:5]
            
            all_scores = list(mcq_scores) + list(tf_scores) + list(qa_scores)
            if all_scores:
                avg_score = sum(all_scores) / len(all_scores)
                if avg_score < 50:
                    at_risk += 1
        
        # Completion rate (chapters with completed study sessions)
        total_chapters = Chapter.objects.filter(is_active=True).count()
        if total_chapters > 0:
            completed_sessions = StudySession.objects.filter(completed=True)
            if filters and filters.get('level'):
                completed_sessions = completed_sessions.filter(user__student_profile__level=filters['level'])
            unique_completions = completed_sessions.values('user', 'chapter').distinct().count()
            # Estimate average completion rate
            completion_rate = min(100, (unique_completions * 100) / (students.count() * total_chapters) if students.count() > 0 else 0)
        else:
            completion_rate = 0
        
        return {
            'total_students': total_students,
            'active_students': active_students,
            'active_percentage': round((active_students / total_students * 100), 1) if total_students > 0 else 0,
            'overall_avg_score': round(overall_avg, 1),
            'completion_rate': round(completion_rate, 1),
            'at_risk_students': at_risk,
            'at_risk_percentage': round((at_risk / total_students * 100), 1) if total_students > 0 else 0,
        }
    
    # ========== COMPONENT 2: PROGRESSION BY UE/CHAPTER ==========
    def get_progression_by_ue(self, filters=None):
        """Get progression data per UE (Unite)"""
        ues = Unite.objects.all()
        
        if filters and filters.get('level'):
            ues = ues.filter(level=filters['level'])
        
        progression_data = []
        
        for ue in ues:
            chapters = ue.chapters.filter(is_active=True)
            total_chapters = chapters.count()
            
            if total_chapters == 0:
                continue
            
            # Get students enrolled in this UE (with activity)
            students_in_ue = User.objects.filter(
                is_student=True,
                studysession__chapter__ue=ue
            ).distinct()
            
            if filters and filters.get('level'):
                students_in_ue = students_in_ue.filter(student_profile__level=filters['level'])
            
            # Fallback: if no study sessions, check quiz results
            if not students_in_ue.exists():
                students_in_ue = User.objects.filter(
                    is_student=True
                ).filter(
                    Q(mcqresult__chapter__ue=ue) |
                    Q(truefalseresult__chapter__ue=ue) |
                    Q(qaresult__chapter__ue=ue)
                ).distinct()
                if filters and filters.get('level'):
                    students_in_ue = students_in_ue.filter(student_profile__level=filters['level'])
            
            total_students_in_ue = students_in_ue.count()
            
            if total_students_in_ue == 0:
                continue
            
            # Calculate completion rate for this UE
            completed_sessions = StudySession.objects.filter(
                chapter__ue=ue, 
                completed=True
            )
            if filters and filters.get('level'):
                completed_sessions = completed_sessions.filter(user__student_profile__level=filters['level'])
            
            unique_completions = completed_sessions.values('user', 'chapter').distinct().count()
            completion_rate = (unique_completions * 100) / (total_students_in_ue * total_chapters)
            
            # Calculate average score for this UE
            mcq_avg = MCQResult.objects.filter(chapter__ue=ue).aggregate(avg=Avg('score'))['avg'] or 0
            tf_avg = TrueFalseResult.objects.filter(chapter__ue=ue).aggregate(avg=Avg('score'))['avg'] or 0
            qa_avg = QAResult.objects.filter(chapter__ue=ue).aggregate(avg=Avg('score'))['avg'] or 0
            
            if filters and filters.get('level'):
                mcq_avg = MCQResult.objects.filter(chapter__ue=ue, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                tf_avg = TrueFalseResult.objects.filter(chapter__ue=ue, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                qa_avg = QAResult.objects.filter(chapter__ue=ue, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
            
            valid_scores = [s for s in [mcq_avg, tf_avg, qa_avg] if s > 0]
            avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            
            progression_data.append({
                'id': ue.id,
                'name': ue.title,
                'level': ue.level,
                'semester': ue.semester,
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1),
                'total_chapters': total_chapters,
                'total_students': total_students_in_ue,
            })
        
        # Sort by level
        level_order = {'paces': 1, '2ème année': 2, '3ème année': 3, '4ème année': 4, '5ème année': 5, '6ème année': 6, 'interne': 7}
        progression_data.sort(key=lambda x: level_order.get(x['level'], 99))
        
        return progression_data

    def get_chapter_details(self, ue_id, filters=None):
        """Get detailed chapter data for a specific UE"""
        chapters = Chapter.objects.filter(ue_id=ue_id, is_active=True).order_by('order')
        
        chapter_data = []
        for chapter in chapters:
            # Get students who have activity in this specific chapter
            students_in_chapter = User.objects.filter(
                is_student=True,
                studysession__chapter=chapter
            ).distinct()
            
            if filters and filters.get('level'):
                students_in_chapter = students_in_chapter.filter(student_profile__level=filters['level'])
            
            # Fallback: if no study sessions, check quiz results for this chapter
            if not students_in_chapter.exists():
                students_in_chapter = User.objects.filter(
                    is_student=True
                ).filter(
                    Q(mcqresult__chapter=chapter) |
                    Q(truefalseresult__chapter=chapter) |
                    Q(qaresult__chapter=chapter)
                ).distinct()
                if filters and filters.get('level'):
                    students_in_chapter = students_in_chapter.filter(student_profile__level=filters['level'])
            
            total_students_in_chapter = students_in_chapter.count()
            
            if total_students_in_chapter == 0:
                continue
            
            # Completion for this chapter
            completed_count = StudySession.objects.filter(
                chapter=chapter, 
                completed=True
            )
            if filters and filters.get('level'):
                completed_count = completed_count.filter(user__student_profile__level=filters['level'])
            completed_count = completed_count.values('user').distinct().count()
            
            completion_rate = (completed_count / total_students_in_chapter * 100) if total_students_in_chapter > 0 else 0
            
            # Average scores for this chapter
            mcq_avg = MCQResult.objects.filter(chapter=chapter).aggregate(avg=Avg('score'))['avg'] or 0
            tf_avg = TrueFalseResult.objects.filter(chapter=chapter).aggregate(avg=Avg('score'))['avg'] or 0
            qa_avg = QAResult.objects.filter(chapter=chapter).aggregate(avg=Avg('score'))['avg'] or 0
            
            if filters and filters.get('level'):
                mcq_avg = MCQResult.objects.filter(chapter=chapter, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                tf_avg = TrueFalseResult.objects.filter(chapter=chapter, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
                qa_avg = QAResult.objects.filter(chapter=chapter, student__student_profile__level=filters['level']).aggregate(avg=Avg('score'))['avg'] or 0
            
            valid_scores = [s for s in [mcq_avg, tf_avg, qa_avg] if s > 0]
            avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0
            
            # Study time for this chapter
            study_time = StudySession.objects.filter(chapter=chapter).aggregate(total=Sum('duration_seconds'))['total'] or 0
            
            chapter_data.append({
                'id': chapter.id,
                'title': chapter.title,
                'prof': chapter.prof,
                'order': chapter.order,
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1),
                'study_time_hours': round(study_time / 3600, 1),
                'students_completed': completed_count,
                'total_students': total_students_in_chapter,
            })
        
        return chapter_data
    
    # ========== COMPONENT 3: STUDENT DEEP DIVE ==========
    def get_student_detailed_progress(self, student_id, filters=None):
        """Get detailed progress for a specific student"""
        try:
            student = User.objects.get(id=student_id, is_student=True)
        except User.DoesNotExist:
            return None
        
        # Get all UEs
        ues = Unite.objects.all()
        if filters and filters.get('level'):
            ues = ues.filter(level=filters['level'])
        
        ue_progress = []
        for ue in ues:
            chapters = ue.chapters.filter(is_active=True)
            
            # Completed chapters
            completed_chapters = StudySession.objects.filter(
                user=student,
                chapter__ue=ue,
                completed=True
            ).values_list('chapter_id', flat=True).distinct()
            
            completion_rate = (completed_chapters.count() / chapters.count() * 100) if chapters.count() > 0 else 0
            
            # Average scores
            mcq_scores = MCQResult.objects.filter(student=student, chapter__ue=ue).values_list('score', flat=True)
            tf_scores = TrueFalseResult.objects.filter(student=student, chapter__ue=ue).values_list('score', flat=True)
            qa_scores = QAResult.objects.filter(student=student, chapter__ue=ue).values_list('score', flat=True)
            
            all_scores = list(mcq_scores) + list(tf_scores) + list(qa_scores)
            avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
            
            # Total study time
            study_time = StudySession.objects.filter(user=student, chapter__ue=ue).aggregate(total=Sum('duration_seconds'))['total'] or 0
            
            ue_progress.append({
                'ue_id': ue.id,
                'ue_name': ue.title,
                'completion_rate': round(completion_rate, 1),
                'avg_score': round(avg_score, 1),
                'chapters_completed': completed_chapters.count(),
                'total_chapters': chapters.count(),
                'study_time_hours': round(study_time / 3600, 1),
            })
        
        # Get recent activity
        recent_activity = []
        
        # Recent quiz attempts
        recent_mcq = MCQResult.objects.filter(student=student).order_by('-created_at')[:5]
        for result in recent_mcq:
            recent_activity.append({
                'date': result.created_at,
                'type': 'MCQ Quiz',
                'chapter': result.chapter.title if result.chapter else 'N/A',
                'score': result.score,
                'details': f"Score: {result.score}%"
            })
        
        recent_tf = TrueFalseResult.objects.filter(student=student).order_by('-created_at')[:5]
        for result in recent_tf:
            recent_activity.append({
                'date': result.created_at,
                'type': 'True/False Quiz',
                'chapter': result.chapter.title if result.chapter else 'N/A',
                'score': result.score,
                'details': f"Score: {result.score}%"
            })
        
        # Recent study sessions
        recent_sessions = StudySession.objects.filter(user=student).order_by('-start_time')[:5]
        for session in recent_sessions:
            duration_min = int(session.duration_seconds / 60) if session.duration_seconds else 0
            recent_activity.append({
                'date': session.start_time,
                'type': 'Study Session',
                'chapter': session.chapter.title if session.chapter else 'N/A',
                'duration': duration_min,
                'details': f"Studied for {duration_min} minutes"
            })
        
        # Sort by date
        recent_activity.sort(key=lambda x: x['date'], reverse=True)
        
        # Get weak areas (chapters with low scores)
        weak_areas = []
        chapters = Chapter.objects.filter(is_active=True)
        for chapter in chapters:
            mcq_score = MCQResult.objects.filter(student=student, chapter=chapter).aggregate(avg=Avg('score'))['avg']
            tf_score = TrueFalseResult.objects.filter(student=student, chapter=chapter).aggregate(avg=Avg('score'))['avg']
            qa_score = QAResult.objects.filter(student=student, chapter=chapter).aggregate(avg=Avg('score'))['avg']
            
            scores = [s for s in [mcq_score, tf_score, qa_score] if s is not None]
            if scores:
                avg_chapter_score = sum(scores) / len(scores)
                if avg_chapter_score < 60:
                    weak_areas.append({
                        'chapter_id': chapter.id,
                        'chapter_title': chapter.title,
                        'ue_name': chapter.ue.title,
                        'avg_score': round(avg_chapter_score, 1),
                    })
        
        weak_areas.sort(key=lambda x: x['avg_score'])
        
        # Flashcard progress
        flashcard_stats = UserProgress.objects.filter(user=student).aggregate(
            total_studied=Count('id'),
            mastered=Count('id', filter=Q(mastered=True)),
            avg_confidence=Avg('confidence_level')
        )
        
        # Annotation activity
        annotation_count = UserAnnotation.objects.filter(user=student).count()
        
        return {
            'student': {
                'id': student.id,
                'name': student.display_name,
                'email': student.email,
                'level': student.student_profile.level if hasattr(student, 'student_profile') else 'N/A',
                'student_id': student.student_profile.student_id_number if hasattr(student, 'student_profile') else 'N/A',
            },
            'ue_progress': ue_progress,
            'recent_activity': recent_activity[:10],
            'weak_areas': weak_areas[:10],
            'flashcard_stats': {
                'total_studied': flashcard_stats['total_studied'] or 0,
                'mastered': flashcard_stats['mastered'] or 0,
                'mastery_rate': round((flashcard_stats['mastered'] / flashcard_stats['total_studied'] * 100), 1) if flashcard_stats['total_studied'] > 0 else 0,
                'avg_confidence': round(flashcard_stats['avg_confidence'] or 0, 1),
            },
            'annotation_count': annotation_count,
        }
    
    # ========== COMPONENT 4: PERFORMANCE DISTRIBUTION ==========
    def get_performance_distribution(self, filters=None):
        """Get score distribution histogram data"""
        # Collect all scores from all quiz types
        scores = []
        
        # Get MCQ scores
        mcq_scores = MCQResult.objects.filter(student__is_student=True)
        if filters:
            if filters.get('level'):
                mcq_scores = mcq_scores.filter(student__student_profile__level=filters['level'])
            if filters.get('unite'):
                mcq_scores = mcq_scores.filter(chapter__ue_id=filters['unite'])
        
        for result in mcq_scores:
            if result.score is not None:
                scores.append(float(result.score))
        
        # Get True/False scores
        tf_scores = TrueFalseResult.objects.filter(student__is_student=True)
        if filters:
            if filters.get('level'):
                tf_scores = tf_scores.filter(student__student_profile__level=filters['level'])
            if filters.get('unite'):
                tf_scores = tf_scores.filter(chapter__ue_id=filters['unite'])
        
        for result in tf_scores:
            if result.score is not None:
                scores.append(float(result.score))
        
        # Get Q&A scores
        qa_scores = QAResult.objects.filter(student__is_student=True)
        if filters:
            if filters.get('level'):
                qa_scores = qa_scores.filter(student__student_profile__level=filters['level'])
            if filters.get('unite'):
                qa_scores = qa_scores.filter(chapter__ue_id=filters['unite'])
        
        for result in qa_scores:
            if result.score is not None:
                scores.append(float(result.score))
        
        if not scores:
            return {
                'distribution': [],
                'total_attempts': 0,
                'average_score': 0,
                'median_score': 0,
                'top_performers': [],
                'bottom_performers': [],
                'student_count': 0,
            }
        
        # Function to determine which bin a score belongs to
        def get_score_bin(score):
            """Return the bin index for a given score (0-7)"""
            if score <= 20:
                return 0
            elif score <= 40:
                return 1
            elif score <= 50:
                return 2
            elif score <= 60:
                return 3
            elif score <= 70:
                return 4
            elif score <= 80:
                return 5
            elif score <= 90:
                return 6
            else:  # score <= 100
                return 7
        
        # Bin labels
        bin_labels = ['0-20', '21-40', '41-50', '51-60', '61-70', '71-80', '81-90', '91-100']
        
        # Count scores in each bin
        bin_counts = [0, 0, 0, 0, 0, 0, 0, 0]
        for score in scores:
            bin_index = get_score_bin(score)
            bin_counts[bin_index] += 1
        
        # Create distribution array
        distribution = []
        for i, label in enumerate(bin_labels):
            distribution.append({
                'range': label,
                'count': bin_counts[i],
                'percentage': round((bin_counts[i] / len(scores) * 100), 1)
            })
        
        # Calculate statistics
        total_attempts = len(scores)
        average_score = round(sum(scores) / total_attempts, 1)
        
        # Calculate median
        sorted_scores = sorted(scores)
        if total_attempts % 2 == 0:
            median_score = round((sorted_scores[total_attempts // 2 - 1] + sorted_scores[total_attempts // 2]) / 2, 1)
        else:
            median_score = round(sorted_scores[total_attempts // 2], 1)
        
        # Get top and bottom performers (students)
        students = User.objects.filter(is_student=True)
        if filters and filters.get('level'):
            students = students.filter(student_profile__level=filters['level'])
        
        student_avg_scores = {}
        for student in students:
            all_scores = []
            all_scores.extend(MCQResult.objects.filter(student=student).values_list('score', flat=True))
            all_scores.extend(TrueFalseResult.objects.filter(student=student).values_list('score', flat=True))
            all_scores.extend(QAResult.objects.filter(student=student).values_list('score', flat=True))
            
            # Filter out None values
            all_scores = [s for s in all_scores if s is not None]
            
            if all_scores:
                student_avg_scores[student.id] = {
                    'id': student.id,
                    'name': student.display_name,
                    'level': student.student_profile.level if hasattr(student, 'student_profile') else 'N/A',
                    'avg_score': sum(all_scores) / len(all_scores),
                    'quiz_count': len(all_scores),
                }
        
        # Sort by score
        sorted_students = sorted(student_avg_scores.values(), key=lambda x: x['avg_score'], reverse=True)
        
        # Top performers (top 10 or at least 5)
        top_count = max(5, int(len(sorted_students) * 0.1))
        top_performers = sorted_students[:top_count]
        
        # Bottom performers (bottom 5)
        bottom_performers = sorted_students[-5:] if len(sorted_students) >= 5 else sorted_students
        bottom_performers.reverse()
        
        return {
            'distribution': distribution,
            'total_attempts': total_attempts,
            'average_score': average_score,
            'median_score': median_score,
            'top_performers': top_performers,
            'bottom_performers': bottom_performers,
            'student_count': len(student_avg_scores),
        }

    # ========== COMPONENT 5: TIME-BASED ANALYTICS ==========
    def get_time_based_analytics(self, filters=None):
        """Get study time and activity trends"""
        
        # Get base queryset for study sessions
        study_sessions = StudySession.objects.filter(user__is_student=True)
        
        # Apply filters
        if filters:
            if filters.get('level'):
                study_sessions = study_sessions.filter(user__student_profile__level=filters['level'])
            if filters.get('unite'):
                study_sessions = study_sessions.filter(chapter__ue_id=filters['unite'])
            if filters.get('chapter'):
                study_sessions = study_sessions.filter(chapter_id=filters['chapter'])
            if filters.get('student'):
                study_sessions = study_sessions.filter(user_id=filters['student'])
            if filters.get('date_from'):
                study_sessions = study_sessions.filter(start_time__date__gte=filters['date_from'])
            if filters.get('date_to'):
                study_sessions = study_sessions.filter(start_time__date__lte=filters['date_to'])
        
        # Debug: Print study session count
        print(f"DEBUG - Total study sessions (after filters): {study_sessions.count()}")
        
        # Get all study sessions with their dates
        all_sessions = study_sessions.filter(start_time__isnull=False).order_by('start_time')
        
        if all_sessions.exists():
            # Get date range
            min_date = all_sessions.first().start_time.date()
            max_date = all_sessions.last().start_time.date()
            
            # Ensure we show at least 30 days
            today = timezone.now().date()
            if (max_date - min_date).days < 30:
                min_date = max_date - timedelta(days=30)
        else:
            # No data, use last 30 days as placeholder
            today = timezone.now().date()
            max_date = today
            min_date = max_date - timedelta(days=30)
        
        # Create date range dictionary
        date_range_sessions = {}
        date_range_hours = {}
        current_date = min_date
        while current_date <= max_date:
            date_str = current_date.strftime('%Y-%m-%d')
            date_range_sessions[date_str] = 0
            date_range_hours[date_str] = 0.0
            current_date += timedelta(days=1)
        
        # Count sessions and sum duration manually
        for session in all_sessions:
            if session.start_time:
                date_str = session.start_time.strftime('%Y-%m-%d')
                if date_str in date_range_sessions:
                    date_range_sessions[date_str] += 1
                    # Convert duration_seconds to hours and add
                    if session.duration_seconds:
                        date_range_hours[date_str] += session.duration_seconds / 3600.0
        
        # Convert to list format for chart
        daily_study = []
        for date_str in date_range_sessions.keys():
            daily_study.append({
                'date': date_str, 
                'sessions': date_range_sessions[date_str],
                'hours': round(date_range_hours[date_str], 1)  # Round to 1 decimal place
            })
        
        print(f"DEBUG - Total study sessions: {study_sessions.count()}")
        print(f"DEBUG - All sessions count: {all_sessions.count()}")
        print(f"DEBUG - Daily date range: from {min_date} to {max_date}")
        print(f"DEBUG - Number of days in range: {len(daily_study)}")
        
        # Calculate statistics
        non_zero_days = sum(1 for d in daily_study if d['sessions'] > 0)
        total_hours = sum(d['hours'] for d in daily_study)
        print(f"DEBUG - Days with study activity: {non_zero_days}")
        print(f"DEBUG - Total study hours: {total_hours}")
        
        # Print sample of days with activity
        sample_days = [d for d in daily_study if d['sessions'] > 0][:10]
        print(f"DEBUG - Sample activity days: {sample_days}")
        
        # ========== Weekly quiz attempts ==========
        mcq_results = MCQResult.objects.filter(student__is_student=True)
        tf_results = TrueFalseResult.objects.filter(student__is_student=True)
        qa_results = QAResult.objects.filter(student__is_student=True)
        
        # Apply same filters to quiz results
        if filters:
            if filters.get('level'):
                mcq_results = mcq_results.filter(student__student_profile__level=filters['level'])
                tf_results = tf_results.filter(student__student_profile__level=filters['level'])
                qa_results = qa_results.filter(student__student_profile__level=filters['level'])
            if filters.get('unite'):
                mcq_results = mcq_results.filter(chapter__ue_id=filters['unite'])
                tf_results = tf_results.filter(chapter__ue_id=filters['unite'])
                qa_results = qa_results.filter(chapter__ue_id=filters['unite'])
            if filters.get('chapter'):
                mcq_results = mcq_results.filter(chapter_id=filters['chapter'])
                tf_results = tf_results.filter(chapter_id=filters['chapter'])
                qa_results = qa_results.filter(chapter_id=filters['chapter'])
            if filters.get('student'):
                mcq_results = mcq_results.filter(student_id=filters['student'])
                tf_results = tf_results.filter(student_id=filters['student'])
                qa_results = qa_results.filter(student_id=filters['student'])
            if filters.get('date_from'):
                mcq_results = mcq_results.filter(created_at__date__gte=filters['date_from'])
                tf_results = tf_results.filter(created_at__date__gte=filters['date_from'])
                qa_results = qa_results.filter(created_at__date__gte=filters['date_from'])
            if filters.get('date_to'):
                mcq_results = mcq_results.filter(created_at__date__lte=filters['date_to'])
                tf_results = tf_results.filter(created_at__date__lte=filters['date_to'])
                qa_results = qa_results.filter(created_at__date__lte=filters['date_to'])
        
        # Collect all quiz attempt dates
        quiz_attempts = []
        
        for result in mcq_results:
            if result.created_at:
                quiz_attempts.append({
                    'date': result.created_at.date(),
                    'type': 'mcq'
                })
        
        for result in tf_results:
            if result.created_at:
                quiz_attempts.append({
                    'date': result.created_at.date(),
                    'type': 'tf'
                })
        
        for result in qa_results:
            if result.created_at:
                quiz_attempts.append({
                    'date': result.created_at.date(),
                    'type': 'qa'
                })
        
        weekly_quiz = []
        
        if quiz_attempts:
            quiz_attempts.sort(key=lambda x: x['date'])
            
            min_quiz_date = quiz_attempts[0]['date']
            max_quiz_date = quiz_attempts[-1]['date']
            
            weeks_diff = ((max_quiz_date - min_quiz_date).days // 7) + 1
            weeks_to_show = max(4, min(12, weeks_diff))
            
            end_date = max_quiz_date
            start_date = end_date - timedelta(days=weeks_to_show * 7)
            
            for week_offset in range(weeks_to_show):
                week_end = end_date - timedelta(days=week_offset * 7)
                week_start = week_end - timedelta(days=6)
                
                mcq_count = 0
                tf_count = 0
                qa_count = 0
                
                for attempt in quiz_attempts:
                    if week_start <= attempt['date'] <= week_end:
                        if attempt['type'] == 'mcq':
                            mcq_count += 1
                        elif attempt['type'] == 'tf':
                            tf_count += 1
                        elif attempt['type'] == 'qa':
                            qa_count += 1
                
                week_label = f"Week {weeks_to_show - week_offset}"
                weekly_quiz.append({
                    'week': week_label,
                    'mcq': mcq_count,
                    'tf': tf_count,
                    'qa': qa_count,
                    'total': mcq_count + tf_count + qa_count,
                })
            
            weekly_quiz.reverse()
        else:
            today = timezone.now().date()
            for i in range(4):
                week_end = today - timedelta(days=i * 7)
                week_label = f"Week {4 - i}"
                weekly_quiz.insert(0, {
                    'week': week_label,
                    'mcq': 0,
                    'tf': 0,
                    'qa': 0,
                    'total': 0,
                })
        
        # Debug output
        total_mcq = mcq_results.count()
        total_tf = tf_results.count()
        total_qa = qa_results.count()
        
        print(f"DEBUG - Final daily study points: {len(daily_study)}")
        print(f"DEBUG - Days with sessions: {len([d for d in daily_study if d['sessions'] > 0])}")
        print(f"DEBUG - Days with hours: {len([d for d in daily_study if d['hours'] > 0])}")
        
        return {
            'daily_study': daily_study,
            'weekly_quiz': weekly_quiz,
            'chapter_time': [],
            'weekday_activity': [],
            'stats': {
                'total_study_sessions': study_sessions.count(),
                'days_with_activity': non_zero_days,
                'total_study_hours': round(total_hours, 1),
                'date_range_start': min_date.strftime('%Y-%m-%d'),
                'date_range_end': max_date.strftime('%Y-%m-%d'),
            }
        }


    # ========== COMPONENT 6: ENGAGEMENT METRICS ==========
    def get_engagement_metrics(self, filters=None):
        """Get student engagement metrics"""
        students = User.objects.filter(is_student=True)
        if filters and filters.get('level'):
            students = students.filter(student_profile__level=filters['level'])
        
        total_students = students.count()
        
        # Annotation activity
        annotations = UserAnnotation.objects.filter(user__is_student=True)
        if filters and filters.get('level'):
            annotations = annotations.filter(user__student_profile__level=filters['level'])
        
        annotation_stats = annotations.aggregate(
            total=Count('id'),
            unique_students=Count('user', distinct=True),
            avg_per_student=Count('id') / total_students if total_students > 0 else 0
        )
        
        # Flashcard engagement
        flashcard_progress = UserProgress.objects.filter(user__is_student=True)
        if filters and filters.get('level'):
            flashcard_progress = flashcard_progress.filter(user__student_profile__level=filters['level'])
        
        flashcard_stats = flashcard_progress.aggregate(
            total_cards_studied=Count('id'),
            mastered_cards=Count('id', filter=Q(mastered=True)),
            unique_students=Count('user', distinct=True),
            avg_confidence=Avg('confidence_level'),
            avg_times_studied=Avg('times_studied'),
        )
        
        # Active vs inactive breakdown
        week_ago = timezone.now() - timedelta(days=7)
        month_ago = timezone.now() - timedelta(days=30)
        
        active_7d = students.filter(
            Q(studysession__start_time__gte=week_ago) |
            Q(mcqresult__created_at__gte=week_ago) |
            Q(truefalseresult__created_at__gte=week_ago) |
            Q(qaresult__created_at__gte=week_ago)
        ).distinct().count()
        
        active_30d = students.filter(
            Q(studysession__start_time__gte=month_ago) |
            Q(mcqresult__created_at__gte=month_ago) |
            Q(truefalseresult__created_at__gte=month_ago) |
            Q(qaresult__created_at__gte=month_ago)
        ).distinct().count()
        
        inactive_30d = total_students - active_30d
        
        # Quiz engagement by type
        quiz_engagement = {
            'mcq': MCQResult.objects.filter(student__is_student=True).count(),
            'truefalse': TrueFalseResult.objects.filter(student__is_student=True).count(),
            'qa': QAResult.objects.filter(student__is_student=True).count(),
        }
        
        if filters and filters.get('level'):
            quiz_engagement['mcq'] = MCQResult.objects.filter(student__student_profile__level=filters['level']).count()
            quiz_engagement['truefalse'] = TrueFalseResult.objects.filter(student__student_profile__level=filters['level']).count()
            quiz_engagement['qa'] = QAResult.objects.filter(student__student_profile__level=filters['level']).count()
        
        # Study session engagement
        study_stats = StudySession.objects.filter(user__is_student=True)
        if filters and filters.get('level'):
            study_stats = study_stats.filter(user__student_profile__level=filters['level'])
        
        study_hours = study_stats.aggregate(total=Sum('duration_seconds'))['total'] or 0
        avg_session_duration = study_stats.aggregate(avg=Avg('duration_seconds'))['avg'] or 0
        
        # Annotation by chapter (most annotated content)
        top_annotated_chapters = UserAnnotation.objects.filter(user__is_student=True)\
            .values('copy__chapter__title', 'copy__chapter__id')\
            .annotate(count=Count('id'))\
            .order_by('-count')[:10]
        
        return {
            'annotation': {
                'total': annotation_stats['total'],
                'students_annotating': annotation_stats['unique_students'],
                'percentage': round((annotation_stats['unique_students'] / total_students * 100), 1) if total_students > 0 else 0,
                'avg_per_student': round(annotation_stats['avg_per_student'], 1),
            },
            'flashcard': {
                'total_students_using': flashcard_stats['unique_students'],
                'percentage': round((flashcard_stats['unique_students'] / total_students * 100), 1) if total_students > 0 else 0,
                'total_cards_studied': flashcard_stats['total_cards_studied'],
                'mastered_cards': flashcard_stats['mastered_cards'],
                'mastery_rate': round((flashcard_stats['mastered_cards'] / flashcard_stats['total_cards_studied'] * 100), 1) if flashcard_stats['total_cards_studied'] > 0 else 0,
                'avg_confidence': round(flashcard_stats['avg_confidence'] or 0, 1),
                'avg_times_studied': round(flashcard_stats['avg_times_studied'] or 0, 1),
            },
            'activity_breakdown': {
                'active_7d': active_7d,
                'active_7d_percentage': round((active_7d / total_students * 100), 1) if total_students > 0 else 0,
                'active_30d': active_30d,
                'active_30d_percentage': round((active_30d / total_students * 100), 1) if total_students > 0 else 0,
                'inactive_30d': inactive_30d,
                'inactive_30d_percentage': round((inactive_30d / total_students * 100), 1) if total_students > 0 else 0,
            },
            'quiz_engagement': quiz_engagement,
            'study_engagement': {
                'total_study_hours': round(study_hours / 3600, 1),
                'avg_session_minutes': round(avg_session_duration / 60, 1),
                'total_sessions': study_stats.count(),
            },
            'top_annotated_chapters': list(top_annotated_chapters),
        }
    

def dashboard_home(request):
    """Main dashboard view"""
    context = {
        'levels': StudentProfile.LEVEL_CHOICES,
        'unites': Unite.objects.all(),
        'chapters': Chapter.objects.filter(is_active=True),
        'students': User.objects.filter(is_student=True),
    }
    
    # Load initial data
    dashboard = StudentProgressionDashboard(request)
    context['kpis'] = dashboard.get_global_kpis()
    context['progression_by_ue'] = dashboard.get_progression_by_ue()
    context['performance_distribution'] = dashboard.get_performance_distribution()
    context['time_analytics'] = dashboard.get_time_based_analytics()
    context['engagement'] = dashboard.get_engagement_metrics()
    
    return render(request, 'dashboard/partials/study_progression.html', context)


@require_http_methods(["GET"])
def get_student_detail_api(request, student_id):
    """Get detailed student data for deep dive"""
    dashboard = StudentProgressionDashboard(request)
    data = dashboard.get_student_detailed_progress(student_id)
    
    if data:
        return JsonResponse({'success': True, 'data': data})
    return JsonResponse({'success': False, 'error': 'Student not found'})


@require_http_methods(["GET"])
def get_chapter_detail_api(request, ue_id):
    """Get chapter details for a specific UE"""
    dashboard = StudentProgressionDashboard(request)
    data = dashboard.get_chapter_details(ue_id)
    return JsonResponse({'success': True, 'data': data})


@require_http_methods(["GET"])
def get_unites_by_level(request):
    """Get unites filtered by level (cascading filter)"""
    level = request.GET.get('level')
    if level:
        unites = Unite.objects.filter(level=level).values('id', 'title', 'level', 'semester')
    else:
        unites = Unite.objects.all().values('id', 'title', 'level', 'semester')
    return JsonResponse({'success': True, 'unites': list(unites)})


@require_http_methods(["GET"])
def get_chapters_by_unite(request):
    """Get chapters filtered by unite (cascading filter)"""
    unite_id = request.GET.get('unite_id')
    if unite_id:
        chapters = Chapter.objects.filter(ue_id=unite_id, is_active=True).values('id', 'title', 'order')
    else:
        chapters = []
    return JsonResponse({'success': True, 'chapters': list(chapters)})


@require_http_methods(["GET"])
def get_students_by_level(request):
    """Get students filtered by level (cascading filter)"""
    level = request.GET.get('level')
    if level:
        students = User.objects.filter(
            is_student=True, 
            student_profile__level=level
        ).values('id', 'first_name', 'last_name', 'email')
    else:
        students = User.objects.filter(is_student=True).values('id', 'first_name', 'last_name', 'email')
    
    # Format display names
    for student in students:
        student['display_name'] = f"{student['first_name']} {student['last_name']}".strip() or student['email']
    
    return JsonResponse({'success': True, 'students': list(students)})


@require_http_methods(["GET"])
def get_at_risk_students_list(request):
    """Get detailed list of at-risk students"""
    filters = {}
    level = request.GET.get('level')
    if level:
        filters['level'] = level
    
    students_data = []
    students = User.objects.filter(is_student=True)
    if level:
        students = students.filter(student_profile__level=level)
    
    for student in students:
        # Get average scores
        mcq_scores = MCQResult.objects.filter(student=student).values_list('score', flat=True)[:10]
        tf_scores = TrueFalseResult.objects.filter(student=student).values_list('score', flat=True)[:10]
        qa_scores = QAResult.objects.filter(student=student).values_list('score', flat=True)[:10]
        
        all_scores = list(mcq_scores) + list(tf_scores) + list(qa_scores)
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            if avg_score < 50:
                # Get last activity date
                last_activity = None
                last_mcq = MCQResult.objects.filter(student=student).order_by('-created_at').first()
                last_tf = TrueFalseResult.objects.filter(student=student).order_by('-created_at').first()
                last_study = StudySession.objects.filter(user=student).order_by('-start_time').first()
                
                activity_dates = []
                if last_mcq:
                    activity_dates.append(last_mcq.created_at)
                if last_tf:
                    activity_dates.append(last_tf.created_at)
                if last_study:
                    activity_dates.append(last_study.start_time)
                
                if activity_dates:
                    last_activity = max(activity_dates)
                
                students_data.append({
                    'id': student.id,
                    'name': student.display_name,
                    'level': student.student_profile.level if hasattr(student, 'student_profile') else 'N/A',
                    'email': student.email,
                    'avg_score': round(avg_score, 1),
                    'quiz_count': len(all_scores),
                    'last_activity': last_activity.strftime('%Y-%m-%d %H:%M') if last_activity else 'Never',
                })
    
    # Sort by lowest score first
    students_data.sort(key=lambda x: x['avg_score'])
    
    return JsonResponse({'success': True, 'students': students_data})


@require_http_methods(["GET"])
def get_top_performers_list(request):
    """Get detailed list of top performers"""
    level = request.GET.get('level')
    
    students_data = []
    students = User.objects.filter(is_student=True)
    if level:
        students = students.filter(student_profile__level=level)
    
    for student in students:
        mcq_scores = MCQResult.objects.filter(student=student).values_list('score', flat=True)
        tf_scores = TrueFalseResult.objects.filter(student=student).values_list('score', flat=True)
        qa_scores = QAResult.objects.filter(student=student).values_list('score', flat=True)
        
        all_scores = list(mcq_scores) + list(tf_scores) + list(qa_scores)
        if all_scores:
            avg_score = sum(all_scores) / len(all_scores)
            students_data.append({
                'id': student.id,
                'name': student.display_name,
                'level': student.student_profile.level if hasattr(student, 'student_profile') else 'N/A',
                'email': student.email,
                'avg_score': round(avg_score, 1),
                'quiz_count': len(all_scores),
            })
    
    # Sort by highest score first
    students_data.sort(key=lambda x: x['avg_score'], reverse=True)
    
    return JsonResponse({'success': True, 'students': students_data})  # Return ALL students


@require_http_methods(["GET"])
def get_active_inactive_students(request):
    """Get lists of active and inactive students"""
    level = request.GET.get('level')
    days = int(request.GET.get('days', 30))
    
    students = User.objects.filter(is_student=True)
    if level:
        students = students.filter(student_profile__level=level)
    
    cutoff_date = timezone.now() - timedelta(days=days)
    
    active_students = []
    inactive_students = []
    
    for student in students:
        last_activity = None
        last_mcq = MCQResult.objects.filter(student=student).order_by('-created_at').first()
        last_tf = TrueFalseResult.objects.filter(student=student).order_by('-created_at').first()
        last_qa = QAResult.objects.filter(student=student).order_by('-created_at').first()
        last_study = StudySession.objects.filter(user=student).order_by('-start_time').first()
        
        activity_dates = []
        if last_mcq:
            activity_dates.append(last_mcq.created_at)
        if last_tf:
            activity_dates.append(last_tf.created_at)
        if last_qa:
            activity_dates.append(last_qa.created_at)
        if last_study:
            activity_dates.append(last_study.start_time)
        
        if activity_dates:
            last_activity = max(activity_dates)
        
        student_info = {
            'id': student.id,
            'name': student.display_name,
            'level': student.student_profile.level if hasattr(student, 'student_profile') else 'N/A',
            'email': student.email,
            'last_activity': last_activity.strftime('%Y-%m-%d %H:%M') if last_activity else 'Never',
        }
        
        if last_activity and last_activity >= cutoff_date:
            active_students.append(student_info)
        else:
            inactive_students.append(student_info)
    
    return JsonResponse({
        'success': True, 
        'active_students': active_students,
        'inactive_students': inactive_students,
        'total_active': len(active_students),
        'total_inactive': len(inactive_students),
    })


@require_http_methods(["GET"])
def debug_quiz_data(request):
    """Debug endpoint to verify quiz data exists"""
    mcq_count = MCQResult.objects.filter(student__is_student=True).count()
    tf_count = TrueFalseResult.objects.filter(student__is_student=True).count()
    qa_count = QAResult.objects.filter(student__is_student=True).count()
    
    # Get sample data
    sample_mcq = MCQResult.objects.filter(student__is_student=True).values('id', 'score', 'created_at', 'student__username')[:5]
    sample_tf = TrueFalseResult.objects.filter(student__is_student=True).values('id', 'score', 'created_at', 'student__username')[:5]
    
    return JsonResponse({
        'success': True,
        'counts': {
            'mcq_results': mcq_count,
            'tf_results': tf_count,
            'qa_results': qa_count,
        },
        'sample_mcq': list(sample_mcq),
        'sample_tf': list(sample_tf),
    })


@require_http_methods(["GET"])
def debug_study_sessions(request):
    """Debug endpoint to verify study session data exists"""
    from lessoncopy.models import StudySession
    from django.utils import timezone
    from datetime import timedelta
    
    total_sessions = StudySession.objects.filter(user__is_student=True).count()
    
    # Get sessions with dates
    sessions_with_dates = StudySession.objects.filter(
        user__is_student=True,
        start_time__isnull=False
    ).values('id', 'start_time', 'duration_seconds', 'completed', 'user__username')[:10]
    
    # Get last 30 days summary
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_sessions = StudySession.objects.filter(
        user__is_student=True,
        start_time__gte=thirty_days_ago
    )
    
    # Daily breakdown for last 30 days
    daily_breakdown = recent_sessions.values('start_time__date').annotate(
        count=Count('id'),
        total_duration=Sum('duration_seconds')
    ).order_by('-start_time__date')
    
    return JsonResponse({
        'success': True,
        'total_study_sessions': total_sessions,
        'recent_sessions_sample': list(sessions_with_dates),
        'daily_breakdown_last_30_days': list(daily_breakdown),
        'has_data': total_sessions > 0,
    })


@require_http_methods(["POST"])
def dashboard_filter(request):
    """AJAX endpoint for filtering dashboard data"""
    try:
        data = json.loads(request.body)
        filters = {
            'level': data.get('level'),
            'unite': data.get('unite'),
            'chapter': data.get('chapter'),
            'student': data.get('student'),
            'date_from': data.get('date_from'),
            'date_to': data.get('date_to'),
        }
        # Remove None values
        filters = {k: v for k, v in filters.items() if v}
        
        dashboard = StudentProgressionDashboard(request)
        
        # Get the time analytics
        time_analytics = dashboard.get_time_based_analytics(filters)
        
        # DEBUG: Print to console
        print("=" * 50)
        print("TIME ANALYTICS DEBUG:")
        print(f"Daily study length: {len(time_analytics.get('daily_study', []))}")
        if time_analytics.get('daily_study'):
            print(f"First 3 daily entries: {time_analytics['daily_study'][:3]}")
            total_sessions = sum(d.get('sessions', 0) for d in time_analytics['daily_study'])
            print(f"Total sessions in data: {total_sessions}")
        print("=" * 50)
        
        response = {
            'kpis': dashboard.get_global_kpis(filters),
            'progression_by_ue': dashboard.get_progression_by_ue(filters),
            'performance_distribution': dashboard.get_performance_distribution(filters),
            'time_analytics': time_analytics,  # Make sure this is included
            'engagement': dashboard.get_engagement_metrics(filters),
        }
        
        # If a specific student is selected, get detailed data
        if filters.get('student'):
            response['student_detail'] = dashboard.get_student_detailed_progress(
                filters['student'], filters
            )
        
        # If a specific UE is selected, get chapter details
        if filters.get('unite') and not filters.get('student'):
            response['chapter_details'] = dashboard.get_chapter_details(
                filters['unite'], filters
            )
        
        return JsonResponse({'success': True, 'data': response})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})



