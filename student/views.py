from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Sum, Q, F, Max
from django.utils import timezone
from datetime import date, timedelta
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, QAResult, TrueFalseResult, MCQAttempt, QAAttempt
from lessoncopy.models import StudySession
# from journal.models import StructuredStudySession
from subscriptions.models import Subscription, Payment, Feature
from utilisateur.models import User
from student.models import StudentProfile
import json
from django.contrib import messages
from .forms import StudentProfileForm
from django.db.models.functions import TruncDate


@login_required
def student_dashboard(request):
    """Comprehensive student dashboard"""
    if not hasattr(request.user, 'student_profile'):
        return redirect('utilisateur:dashboard')
    
    student_profile = request.user.student_profile
    today = date.today()
    
    # ========== SUBSCRIPTION & PAYMENT STATUS ==========
    # Active subscription
    active_subscription = Subscription.objects.filter(
        student=student_profile,
        payement_status='approved',
        start_date__lte=today,
        expires_at__gte=today
    ).first()
    
    # Pending subscription
    pending_subscription = Subscription.objects.filter(
        student=student_profile,
        payement_status='pending'
    ).first()
    
    # Pending payments
    pending_payments = Payment.objects.filter(
        student=student_profile,
        payement_status='pending'
    ).order_by('-created_at')
    
    # Subscription history
    subscription_history = Subscription.objects.filter(
        student=student_profile
    ).exclude(payement_status='pending').order_by('-created_at')[:5]


    # ========== ACCESSIBLE SUBJECTS ==========
    user_level = student_profile.level
    accessible_subjects = Unite.objects.filter(level=user_level)
    
    # Count accessible subjects
    subject_count = accessible_subjects.count()
    
    # Get subjects with available chapters - FIXED RELATIONSHIPS
    subjects_with_content = accessible_subjects.annotate(
        chapter_count=Count('chapters'),
    ).order_by('title')
    
    # Calculate additional metrics separately to avoid complex joins
    for subject in subjects_with_content:
        # Get chapters for this subject
        subject_chapters = Chapter.objects.filter(ue=subject, is_active=True)
        
        # Count completed chapters
        completed_chapters = StudySession.objects.filter(
            user=request.user,
            chapter__in=subject_chapters,
            completed=True
        ).values('chapter').distinct().count()
        
        # Calculate total study time
        total_study_time = StudySession.objects.filter(
            user=request.user,
            chapter__in=subject_chapters
        ).aggregate(total=Sum('duration_seconds'))['total'] or 0
        
        # Add to subject object
        subject.completed_chapters = completed_chapters
        subject.total_study_time = total_study_time
        subject.total_study_hours = round(total_study_time / 3600, 1) if total_study_time > 0 else 0
    
    # ========== QUIZ PERFORMANCE ==========
    # Get quiz statistics

    mcq_stats = MCQResult.objects.filter(
        student=request.user
    ).aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id'),
        best_score=Max('score'),
        last_attempt=Max('created_at')
    )

    mcq_exam_stats = MCQAttempt.objects.filter(
        student=request.user
    ).aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id'),
        best_score=Max('score'),
        last_attempt=Max('start_time')
    )
    
    qa_stats = QAResult.objects.filter(
        student=request.user
    ).aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id'),
        best_score=Max('score'),
        last_attempt=Max('created_at')
    )

    qa_exam_stats = QAAttempt.objects.filter(
        student=request.user
    ).aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id'),
        best_score=Max('score'),
        last_attempt=Max('start_time')
    )
    
    tf_stats = TrueFalseResult.objects.filter(
        student=request.user
    ).aggregate(
        avg_score=Avg('score'),
        total_attempts=Count('id'),
        best_score=Max('score'),
        last_attempt=Max('created_at')
    )
    
    # Recent quiz attempts
    recent_mcqs = MCQResult.objects.filter(
        student=request.user
    ).order_by('-created_at')[:5]
    
    recent_qas = QAResult.objects.filter(
        student=request.user
    ).order_by('-created_at')[:5]
    
    recent_tfs = TrueFalseResult.objects.filter(
        student=request.user
    ).order_by('-created_at')[:5]
    
    # ========== STUDY SESSIONS & SCHEDULES ==========
    # Today's study sessions
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_sessions = StudySession.objects.filter(
        user=request.user,
        start_time__gte=today_start
    ).order_by('-start_time')
    
    # Weekly study time
    week_ago = timezone.now() - timedelta(days=7)
    weekly_study = StudySession.objects.filter(
        user=request.user,
        start_time__gte=week_ago
    ).aggregate(
        total_seconds=Sum('duration_seconds'),
        session_count=Count('id')
    )
    
    weekly_hours = round((weekly_study['total_seconds'] or 0) / 3600, 1)

    # upcoming_schedules = StructuredStudySession.objects.filter(
    #     user=request.user,
    #     status="planned" or "in_progress",
    #     is_completed=False,
    # ).order_by('planned_date')[:5]
    
    # completed_schedules = StructuredStudySession.objects.filter(
    #     user=request.user,
    #     status="completed",
    # ).order_by('-study_date')[:5]

    
    # ========== PROGRESS STATISTICS ==========
    # Total chapters studied
    studied_chapters = StudySession.objects.filter(
        user=request.user,
        completed=True
    ).values('chapter').distinct().count()
    
    # Total available chapters
    total_chapters = Chapter.objects.filter(
        ue__level=user_level, is_active=True
    ).count()
    
    progress_percentage = 0
    if total_chapters > 0:
        progress_percentage = round((studied_chapters / total_chapters) * 100, 1)
    
    # Study streak (consecutive days with study sessions)
    current_streak = calculate_study_streak(request.user)
    
    # ========== FEATURE USAGE ==========
    feature_usage = {}
    if active_subscription and active_subscription.feature:
        feature = active_subscription.feature
        subscription = active_subscription
        
        feature_usage = {
            'mcq': {
                'used': subscription.mcq_attempts_used,
                'total': feature.mcq_features,
                'remaining': subscription.get_remaining_mcq(),
                'percentage': calculate_percentage(subscription.mcq_attempts_used, feature.mcq_features)
            },
            'qa': {
                'used': subscription.qa_attempts_used,
                'total': feature.qa_features,
                'remaining': subscription.get_remaining_qa(),
                'percentage': calculate_percentage(subscription.qa_attempts_used, feature.qa_features)
            },
            'tf': {
                'used': subscription.tf_attempts_used,
                'total': feature.tf_features,
                'remaining': subscription.get_remaining_tf(),
                'percentage': calculate_percentage(subscription.tf_attempts_used, feature.tf_features)
            },
            'mcq_exam': {
                'used': subscription.mcq_exam_attempts_used,
                'total': feature.mcq_exam_feature,
                'remaining': subscription.get_remaining_mcq_exams(),
                'percentage': calculate_percentage(subscription.mcq_exam_attempts_used, feature.mcq_exam_feature)
            },
            'qa_exam': {
                'used': subscription.qa_exam_attempts_used,
                'total': feature.qa_exam_feature,
                'remaining': subscription.get_remaining_qa_exams(),
                'percentage': calculate_percentage(subscription.qa_exam_attempts_used, feature.qa_exam_feature)
            }
        }
    
    # ========== CHARTS DATA ==========
    # Performance trend data (last 30 days)
    performance_data = get_performance_chart_data(request.user)
    
    # Study time distribution
    study_distribution = get_study_distribution_data(request.user)
    
    # Quiz type distribution
    quiz_distribution = get_quiz_distribution_data(request.user)
    
    # ========== NOTIFICATIONS & ALERTS ==========
    alerts = []
    
    # Subscription expiration alert
    # if active_subscription and active_subscription.expires_at:
    #     days_left = (active_subscription.expires_at - today).days
    #     if days_left <= 7:
    #         alerts.append({
    #             'type': 'warning',
    #             'message': f'Votre abonnement expire dans {days_left} jour(s)',
    #             'link': '/subscription/'
    #         })
    
    # # Quiz attempts alert
    # if active_subscription and feature_usage:
    #     for quiz_type, usage in feature_usage.items():
    #         if usage['remaining'] <= 2 and usage['remaining'] > 0:
    #             alerts.append({
    #                 'type': 'info',
    #                 'message': f'Il vous reste {usage["remaining"]} tentatives pour les {quiz_type.upper()}',
    #                 'link': '/quizzes/'
    #             })
    
    # Upcoming schedules alert
    # if upcoming_schedules.exists():
    #     next_schedule = upcoming_schedules.first()
    #     hours_until = (next_schedule.planned_date - timezone.now()).total_seconds() / 3600
    #     if hours_until <= 24:
    #         alerts.append({
    #             'type': 'info',
    #             'message': f'Vous avez un planning de lecture dans {int(hours_until)} heure(s)',
    #             'link': '/schedules/'
    #         })
    
    # ========== QUICK STATS ==========
    # Total study hours
    total_study_seconds = StudySession.objects.filter(
        user=request.user
    ).aggregate(total=Sum('duration_seconds'))['total'] or 0
    total_study_hours = round(total_study_seconds / 3600, 1)
    
    # Overall quiz average
    overall_avg = calculate_overall_average(mcq_stats, qa_stats, tf_stats)
    
    context = {
        # User Info
        'student_profile': student_profile,
        'user_level': user_level,
        
        # Subscription & Payment
        'active_subscription': active_subscription,
        'pending_subscription': pending_subscription,
        'pending_payments': pending_payments,
        'subscription_history': subscription_history,
        
        # Subjects & Content
        'accessible_subjects': accessible_subjects,
        'subject_count': subject_count,
        'subjects_with_content': subjects_with_content,
        
        # Quiz Performance
        'mcq_stats': mcq_stats,
        'mcq_exam_stats': mcq_exam_stats,
        'qa_stats': qa_stats,
        'qa_exam_stats': qa_exam_stats,
        'tf_stats': tf_stats,
        'recent_mcqs': recent_mcqs,
        'recent_qas': recent_qas,
        'recent_tfs': recent_tfs,
        
        # Study Sessions
        'today_sessions': today_sessions,
        'weekly_hours': weekly_hours,
        'weekly_sessions': weekly_study['session_count'] or 0,
            # 'upcoming_schedules': upcoming_schedules,
            # 'completed_schedules': completed_schedules,
        
        # Progress
        'studied_chapters': studied_chapters,
        'total_chapters': total_chapters,
        'progress_percentage': progress_percentage,
        'current_streak': current_streak,
        
        # Feature Usage
        'feature_usage': feature_usage,
        
        # Charts Data
        'performance_data_json': json.dumps(performance_data),
        'study_distribution_json': json.dumps(study_distribution),
        'quiz_distribution_json': json.dumps(quiz_distribution),
        
        # Alerts
        'alerts': alerts,
        
        # Quick Stats
        'quick_stats': {
            'total_quiz_attempts': (mcq_stats['total_attempts'] or 0) + 
                                  (qa_stats['total_attempts'] or 0) + 
                                  (tf_stats['total_attempts'] or 0),
            'avg_quiz_score': overall_avg,
            'total_study_hours': total_study_hours,
            # 'schedules_completed': completed_schedules.count(),
        }
    }
    
    return render(request, 'student/dashboard.html', context)


def calculate_study_streak(user):
    """Calculate consecutive days with study sessions"""
    today = timezone.now().date()
    streak = 0
    
    for i in range(30):  # Check last 30 days
        check_date = today - timedelta(days=i)
        has_study = StudySession.objects.filter(
            user=user,
            start_time__date=check_date
        ).exists()
        
        if has_study:
            streak += 1
        else:
            break
    
    return streak


def calculate_percentage(used, total):
    """Calculate percentage used"""
    if total == 0:
        return 0
    return round((used / total) * 100, 1)


def calculate_overall_average(mcq_stats, qa_stats, tf_stats):
    """Calculate overall quiz average"""
    total_score = 0
    total_weight = 0
    
    if mcq_stats['avg_score'] and mcq_stats['total_attempts']:
        total_score += mcq_stats['avg_score'] * mcq_stats['total_attempts']
        total_weight += mcq_stats['total_attempts']
    
    if qa_stats['avg_score'] and qa_stats['total_attempts']:
        total_score += qa_stats['avg_score'] * qa_stats['total_attempts']
        total_weight += qa_stats['total_attempts']
    
    if tf_stats['avg_score'] and tf_stats['total_attempts']:
        total_score += tf_stats['avg_score'] * tf_stats['total_attempts']
        total_weight += tf_stats['total_attempts']
    
    return round(total_score / total_weight, 1) if total_weight > 0 else 0


def get_performance_chart_data(user, days=30):
    """Get number of quiz attempts per day for MCQ, Q&A, and True/False"""
    from datetime import timedelta
    from django.utils import timezone
    from django.db import connection
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Create a dictionary for all dates in range with zeros as default
    date_range = {}
    current_date = start_date.date()
    end_date_obj = end_date.date()
    while current_date <= end_date_obj:
        date_range[current_date] = {'mcq': 0, 'qa': 0, 'tf': 0}  # Default to 0 instead of None
        current_date += timedelta(days=1)
    
    # Get MCQ attempt counts per day
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DATE(created_at) as quiz_date, COUNT(*) as attempt_count
            FROM quizzes_mcqresult
            WHERE student_id = %s AND created_at >= %s AND created_at <= %s
            GROUP BY DATE(created_at)
            ORDER BY quiz_date
        """, [user.id, start_date, end_date])
        
        for row in cursor.fetchall():
            quiz_date = row[0]
            if quiz_date in date_range:
                date_range[quiz_date]['mcq'] = int(row[1])
    
    # Get Q&A attempt counts per day
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DATE(created_at) as quiz_date, COUNT(*) as attempt_count
            FROM quizzes_qaresult
            WHERE student_id = %s AND created_at >= %s AND created_at <= %s
            GROUP BY DATE(created_at)
            ORDER BY quiz_date
        """, [user.id, start_date, end_date])
        
        for row in cursor.fetchall():
            quiz_date = row[0]
            if quiz_date in date_range:
                date_range[quiz_date]['qa'] = int(row[1])
    
    # Get True/False attempt counts per day
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT DATE(created_at) as quiz_date, COUNT(*) as attempt_count
            FROM quizzes_truefalseresult
            WHERE student_id = %s AND created_at >= %s AND created_at <= %s
            GROUP BY DATE(created_at)
            ORDER BY quiz_date
        """, [user.id, start_date, end_date])
        
        for row in cursor.fetchall():
            quiz_date = row[0]
            if quiz_date in date_range:
                date_range[quiz_date]['tf'] = int(row[1])
    
    # Build chart data arrays (all values are integers, including zeros)
    labels = []
    mcq_data = []
    qa_data = []
    tf_data = []
    
    for date in sorted(date_range.keys()):
        labels.append(date.strftime('%d/%m'))
        mcq_data.append(date_range[date]['mcq'])
        qa_data.append(date_range[date]['qa'])
        tf_data.append(date_range[date]['tf'])
    
    # Calculate statistics for summary cards
    total_mcq = sum(mcq_data)
    total_qa = sum(qa_data)
    total_tf = sum(tf_data)
    
    # Find days with activity
    days_with_mcq = len([x for x in mcq_data if x > 0])
    days_with_qa = len([x for x in qa_data if x > 0])
    days_with_tf = len([x for x in tf_data if x > 0])
    
    # print(f"DEBUG - Total MCQ attempts: {total_mcq} over {days_with_mcq} days")
    # print(f"DEBUG - Total Q&A attempts: {total_qa} over {days_with_qa} days")
    # print(f"DEBUG - Total TF attempts: {total_tf} over {days_with_tf} days")
    # print(f"DEBUG - Daily average MCQ: {total_mcq/len(labels):.1f}")
    
    return {
        'labels': labels,
        'metadata': {
            'total_mcq': total_mcq,
            'total_qa': total_qa,
            'total_tf': total_tf,
            'days_with_mcq': days_with_mcq,
            'days_with_qa': days_with_qa,
            'days_with_tf': days_with_tf,
            'avg_daily_mcq': round(total_mcq / len(labels), 1) if labels else 0,
            'avg_daily_qa': round(total_qa / len(labels), 1) if labels else 0,
            'avg_daily_tf': round(total_tf / len(labels), 1) if labels else 0,
            'best_day_mcq': max(mcq_data) if mcq_data else 0,
            'best_day_qa': max(qa_data) if qa_data else 0,
            'best_day_tf': max(tf_data) if tf_data else 0,
        },
        'datasets': [
            {
                'label': 'QCM',
                'data': mcq_data,
                'borderColor': '#1a73e8',
                'backgroundColor': 'rgba(26, 115, 232, 0.1)',
                'borderWidth': 2,
                'pointRadius': 4,
                'pointHoverRadius': 8,
                'pointBackgroundColor': '#1a73e8',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'tension': 0.2,
                'fill': True,
                'spanGaps': True,
                'stepped': False
            },
            {
                'label': 'Q&R',
                'data': qa_data,
                'borderColor': '#9c27b0',
                'backgroundColor': 'rgba(156, 39, 176, 0.1)',
                'borderWidth': 2,
                'pointRadius': 4,
                'pointHoverRadius': 8,
                'pointBackgroundColor': '#9c27b0',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'tension': 0.2,
                'fill': True,
                'spanGaps': True,
                'stepped': False
            },
            {
                'label': 'Vrai/Faux',
                'data': tf_data,
                'borderColor': '#ff9800',
                'backgroundColor': 'rgba(255, 152, 0, 0.1)',
                'borderWidth': 2,
                'pointRadius': 4,
                'pointHoverRadius': 8,
                'pointBackgroundColor': '#ff9800',
                'pointBorderColor': '#ffffff',
                'pointBorderWidth': 2,
                'tension': 0.2,
                'fill': True,
                'spanGaps': True,
                'stepped': False
            }
        ]
    }


def get_study_distribution_data(user):
    """Get study time distribution by subject"""
    # Aggregate by subject
    subject_hours = {}
    
    # Use select_related to optimize query
    study_sessions = StudySession.objects.filter(
        user=user,
        duration_seconds__gt=0
    ).select_related('chapter__ue')
    
    for session in study_sessions:
        if session.chapter and session.chapter.ue:
            subject_name = session.chapter.ue.title
            hours = session.duration_seconds / 3600
            subject_hours[subject_name] = subject_hours.get(subject_name, 0) + hours
    
    # Sort by hours and take top 5
    sorted_items = sorted(subject_hours.items(), key=lambda x: x[1], reverse=True)[:5]
    
    labels = [item[0] for item in sorted_items]
    hours = [round(item[1], 1) for item in sorted_items]
    
    # If no data, return placeholder
    if not labels:
        labels = ['Aucune donnée']
        hours = [0]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Heures d\'étude',
            'data': hours,
            'backgroundColor': [
                'rgba(26, 115, 232, 0.7)',
                'rgba(156, 39, 176, 0.7)',
                'rgba(0, 188, 212, 0.7)',
                'rgba(76, 175, 80, 0.7)',
                'rgba(255, 152, 0, 0.7)',
            ],
            'borderWidth': 1
        }]
    }


def get_quiz_distribution_data(user):
    """Get quiz attempts distribution by type"""
    mcq_count = MCQResult.objects.filter(student=user).count()
    qa_count = QAResult.objects.filter(student=user).count()
    tf_count = TrueFalseResult.objects.filter(student=user).count()
    
    # If no data, show placeholder
    if mcq_count == 0 and qa_count == 0 and tf_count == 0:
        return {
            'labels': ['Aucune donnée'],
            'datasets': [{
                'label': 'Tentatives',
                'data': [1],
                'backgroundColor': ['rgba(200, 200, 200, 0.7)'],
                'borderWidth': 1
            }]
        }
    
    return {
        'labels': ['QCM', 'Q&R', 'Vrai/Faux'],
        'datasets': [{
            'label': 'Tentatives',
            'data': [mcq_count, qa_count, tf_count],
            'backgroundColor': [
                'rgba(26, 115, 232, 0.7)',
                'rgba(156, 39, 176, 0.7)',
                'rgba(255, 152, 0, 0.7)',
            ],
            'borderWidth': 1
        }]
    }


# Create your views here.
@login_required
def update_student_profile(request):
    """Update student profile"""
    if not request.user.is_student:
        messages.error(request, "Vous n'êtes pas un étudiant.")
        return redirect('utilisateur:dashboard')
    
    student_profile = get_object_or_404(StudentProfile, user=request.user)
    
    if request.method == 'POST':
        form = StudentProfileForm(request.POST, instance=student_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil étudiant mis à jour avec succès!")
            return redirect('utilisateur:profile')
    else:
        form = StudentProfileForm(instance=student_profile)
    
    return render(request, 'utilisateur/student_profile_update.html', {'form': form})


