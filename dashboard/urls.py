from django.urls import path
from .views import user, study_pregression

app_name = 'dashboard'


urlpatterns = [
    path('user-section/', user.dashboard_user_section, name='dashboard'),
    path('user-section/filter-ajax/', user.dashboard_user_filter_ajax, name='user_filter_ajax'),
]

urlpatterns += [
    path('study-progression/', study_pregression.dashboard_home, name='home'),
    path('api/filter/', study_pregression.dashboard_filter, name='filter'),
    path('api/student/<int:student_id>/', study_pregression.get_student_detail_api, name='student_detail'),
    path('api/chapters/<int:ue_id>/', study_pregression.get_chapter_detail_api, name='chapter_detail'),
    
    # New cascading filter endpoints
    path('api/unites-by-level/', study_pregression.get_unites_by_level, name='unites_by_level'),
    path('api/chapters-by-unite/', study_pregression.get_chapters_by_unite, name='chapters_by_unite'),
    path('api/students-by-level/', study_pregression.get_students_by_level, name='students_by_level'),
    
    # New list endpoints
    path('api/at-risk-students/', study_pregression.get_at_risk_students_list, name='at_risk_students'),
    path('api/top-performers/', study_pregression.get_top_performers_list, name='top_performers'),
    path('api/active-inactive-students/', study_pregression.get_active_inactive_students, name='active_inactive_students'),
    
    path('api/debug-study-sessions/', study_pregression.debug_study_sessions, name='debug_study_sessions'),
    path('api/debug-quiz-data/', study_pregression.debug_quiz_data, name='debug_quiz_data'),
]

