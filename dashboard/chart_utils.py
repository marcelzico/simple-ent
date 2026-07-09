from django.db.models import Count, Avg, Sum
from django.db import models
from django.utils import timezone
from datetime import timedelta, datetime
from collections import OrderedDict
import json
from utilisateur.models import User
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, QAResult, TrueFalseResult
from interactions.models import Message, DiscussionThread, Conversation
from lessoncopy.models import StudySession
from subscriptions.models import Subscription
from datetime import date
from student.models import StudentProfile

def get_user_growth_data(days=30):
    """Get actual user growth data for the chart - MySQL compatible"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get daily user registrations using MySQL-compatible date extraction
    user_data = User.objects.filter(
        date_joined__date__gte=start_date,
        date_joined__date__lte=end_date
    ).extra({
        'date': "DATE(date_joined)"
    }).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Create a complete date range with zeros for missing dates
    date_range = OrderedDict()
    current_date = start_date
    while current_date <= end_date:
        date_range[current_date.strftime('%b %d')] = 0
        current_date += timedelta(days=1)
    
    # Fill in actual data
    for item in user_data:
        date_key = item['date'].strftime('%b %d')
        date_range[date_key] = item['count']
    
    return {
        'labels': list(date_range.keys()),
        'datasets': [{
            'label': 'New Users',
            'data': list(date_range.values()),
            'backgroundColor': 'rgba(54, 162, 235, 0.2)',
            'borderColor': 'rgba(54, 162, 235, 1)',
            'borderWidth': 2,
            'tension': 0.4,
            'fill': True
        }]
    }


# getting student by level
def get_subject_engagement_data():
    """Get student distribution by level of study"""
    # Get count of students by level
    level_data = StudentProfile.objects.filter(
        level__isnull=False
    ).exclude(
        level=''  # Exclude empty levels
    ).values('level').annotate(
        student_count=Count('id')
    ).order_by('student_count')
    
    # Map level codes to full names for better display
    level_names = {
        'paces': 'PACES',
        '2ème année': '2nd Year',
        '3ème année': '3rd Year', 
        '4ème année': '4th Year',
        '5ème année': '5th Year',
        '6ème année': '6th Year',
    }
    
    # Prepare data for chart
    labels = []
    data = []
    
    for item in level_data:
        level_code = item['level']
        level_name = level_names.get(level_code, level_code)
        labels.append(level_name)
        data.append(item['student_count'])
    
    # If no data, provide some sample data
    if not labels:
        labels = ['2nd Year', '3rd Year', '4th Year', '5th Year', '6th Year']
        data = [25, 30, 45, 20, 15]
    
    colors = [
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(75, 192, 192, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)',
        'rgba(83, 102, 255, 0.7)',
        'rgba(40, 159, 64, 0.7)',
    ]
    
    return {
        'labels': labels,
        'datasets': [{
            'label': 'Number of Students',
            'data': data,
            'backgroundColor': colors[:len(labels)],
            'borderColor': colors[:len(labels)],
            'borderWidth': 1
        }]
    }


def get_performance_trends_data(period='month'):
    """Get actual performance trends over time - MySQL compatible"""
    if period == 'week':
        days = 7
        group_by = 'DATE(created_at)'  # Daily for week view
    elif period == 'month':
        days = 30
        group_by = 'YEARWEEK(created_at)'  # Weekly for month view
    else:  # quarter
        days = 90
        group_by = 'YEARWEEK(created_at)'  # Weekly for quarter view
        
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Get performance data using MySQL-compatible date grouping
    mcq_data = MCQResult.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).extra({
        'period': group_by
    }).values('period').annotate(
        avg_score=Avg('score')
    ).order_by('period')
    
    qa_data = QAResult.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).extra({
        'period': group_by
    }).values('period').annotate(
        avg_score=Avg('score')
    ).order_by('period')
    
    # Format data for chart
    labels = []
    mcq_scores = []
    qa_scores = []
    
    # For weekly grouping, convert YEARWEEK to readable format
    if 'YEARWEEK' in group_by:
        for mcq_item in mcq_data:
            # Convert YEARWEEK (e.g., 202401) to readable format
            year_week = str(mcq_item['period'])
            year = year_week[:4]
            week = year_week[4:]
            labels.append(f'W{week}')
            mcq_scores.append(round(mcq_item['avg_score'] or 0, 1))
            
            # Find corresponding Q&A score
            qa_score = next((item['avg_score'] for item in qa_data 
                            if str(item['period']) == year_week), 0)
            qa_scores.append(round(qa_score or 0, 1))
    else:
        # Daily grouping
        for mcq_item in mcq_data:
            date_str = mcq_item['period'].strftime('%b %d')
            labels.append(date_str)
            mcq_scores.append(round(mcq_item['avg_score'] or 0, 1))
            
            qa_score = next((item['avg_score'] for item in qa_data 
                            if item['period'].strftime('%b %d') == date_str), 0)
            qa_scores.append(round(qa_score or 0, 1))
    
    # If no data, provide some sample data to prevent chart errors
    if not labels:
        labels = ['No data']
        mcq_scores = [0]
        qa_scores = [0]
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'MCQ Scores',
                'data': mcq_scores,
                'borderColor': 'rgba(54, 162, 235, 1)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'tension': 0.4,
                'fill': False
            },
            {
                'label': 'Q&A Scores',
                'data': qa_scores,
                'borderColor': 'rgba(255, 99, 132, 1)',
                'backgroundColor': 'rgba(255, 99, 132, 0.1)',
                'tension': 0.4,
                'fill': False
            }
        ]
    }

def get_study_activity_data(days=30):
    """Get study activity data for charts - MySQL compatible"""
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    study_data = StudySession.objects.filter(
        start_time__date__gte=start_date,
        start_time__date__lte=end_date
    ).extra({
        'date': "DATE(start_time)"
    }).values('date').annotate(
        total_hours=Sum('duration_seconds') / 3600,
        session_count=Count('id')
    ).order_by('date')
    
    # Create complete date range
    date_range = OrderedDict()
    current_date = start_date
    while current_date <= end_date:
        date_range[current_date.strftime('%b %d')] = {'hours': 0, 'sessions': 0}
        current_date += timedelta(days=1)
    
    # Fill with actual data
    for item in study_data:
        date_key = item['date'].strftime('%b %d')
        date_range[date_key] = {
            'hours': round(item['total_hours'] or 0, 1),
            'sessions': item['session_count']
        }
    
    labels = list(date_range.keys())
    hours_data = [item['hours'] for item in date_range.values()]
    sessions_data = [item['sessions'] for item in date_range.values()]
    
    return {
        'labels': labels,
        'datasets': [
            {
                'label': 'Study Hours',
                'data': hours_data,
                'borderColor': 'rgba(75, 192, 192, 1)',
                'backgroundColor': 'rgba(75, 192, 192, 0.1)',
                'yAxisID': 'y',
            },
            {
                'label': 'Study Sessions',
                'data': sessions_data,
                'borderColor': 'rgba(153, 102, 255, 1)',
                'backgroundColor': 'rgba(153, 102, 255, 0.1)',
                'yAxisID': 'y1',
            }
        ]
    }

def get_system_stats():
    """Get basic system statistics for the dashboard"""
    total_users = User.objects.count()
    total_students = User.objects.filter(is_student=True).count()

    total_subjects = Unite.objects.count()
    total_chapters = Chapter.objects.count()
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_users_count = User.objects.filter(date_joined__gte=week_ago).count()
    
    return {
        'total_users': total_users,
        'total_students': total_students,
        'total_subjects': total_subjects,
        'total_chapters': total_chapters,
        'recent_users_count': recent_users_count,
    }

def get_subscription_stats():
    """Get subscription statistics"""
    today = date.today()
    
    # Active subscriptions (approved and not expired)
    active_subscriptions = Subscription.objects.filter(
        payement_status='approved',
        start_date__lte=today,
        expires_at__gte=today
    ).count()
    
    # Pending subscriptions
    pending_subscriptions = Subscription.objects.filter(
        payement_status='pending'
    ).count()
    
    # Rejected subscriptions
    rejected_subscriptions = Subscription.objects.filter(
        payement_status='rejected'
    ).count()
    
    # Expired subscriptions
    expired_subscriptions = Subscription.objects.filter(
        payement_status='approved',
        expires_at__lt=today
    ).count()
    
    # Subscription trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_approvals = Subscription.objects.filter(
        payement_status='approved',
        approved_at__gte=thirty_days_ago
    ).count()
    
    # Revenue statistics (sum of approved subscription amounts)
    total_revenue = Subscription.objects.filter(
        payement_status='approved'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Active features distribution
    feature_stats = {}
    active_subs = Subscription.objects.filter(
        payement_status='approved',
        start_date__lte=today,
        expires_at__gte=today
    ).select_related('feature')
    
    for sub in active_subs:
        feature_name = sub.feature.name if sub.feature else "Unknown"
        feature_stats[feature_name] = feature_stats.get(feature_name, 0) + 1
    
    return {
        'active_subscriptions': active_subscriptions,
        'pending_subscriptions': pending_subscriptions,
        'rejected_subscriptions': rejected_subscriptions,
        'expired_subscriptions': expired_subscriptions,
        'recent_approvals': recent_approvals,
        'total_revenue': total_revenue,
        'feature_stats': feature_stats,
    }

def get_study_session_stats():
    """Get study session statistics"""
    total_study_sessions = StudySession.objects.count()
    
    # Calculate total study hours
    total_seconds = StudySession.objects.aggregate(
        total_seconds=Sum('duration_seconds')
    )['total_seconds'] or 0
    total_study_hours = round(total_seconds / 3600, 1)
    
    # Active study sessions (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
    active_sessions = StudySession.objects.filter(
        start_time__gte=seven_days_ago
    ).count()
    
    # Average session length
    avg_session_minutes = 0
    if total_study_sessions > 0:
        avg_session_seconds = total_seconds / total_study_sessions
        avg_session_minutes = round(avg_session_seconds / 60, 1)
    
    return {
        'total_study_sessions': total_study_sessions,
        'total_study_hours': total_study_hours,
        'active_sessions': active_sessions,
        'avg_session_minutes': avg_session_minutes,
    }

def get_interactions_stats():
    """Get interactions statistics"""

    
    # Recent activity (last 7 days)
    seven_days_ago = timezone.now() - timedelta(days=7)
  
    # Most active users
    active_users = User.objects.annotate(
        message_count=Count('messages')
    ).order_by('-message_count')[:5]
    
    return {
        'active_users': active_users,
    }


