from django.urls import path
from . import views, views_student

app_name = 'lecon'

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('create/', views.create_subject, name='create_subject'),
    path('<int:pk>/', views.subject_detail, name='subject_detail'),
    path('subject/<int:unite_id>/edit/', views.update_unite, name='update_unite'),
    path('subject/<int:unite_id>/delete/', views.delete_unite, name='delete_unite'),

    path('<int:unite_id>/chapters/create/', views.create_chapter, name='create_chapter'),
    path('<int:subject_pk>/chapters/<int:chapter_pk>/', views.chapter_detail, name='chapter_detail'),
    path('<int:chapter_id>/edit/', views.edit_chapter, name='edit_chapter'),
    path('chapter/<int:chapter_id>/delete/', views.delete_chapter, name='delete_chapter'),
    
    path('unite/<int:unite_id>/section/create/', views.create_section, name='update_chapter'),
    path('unite/<int:unite_id>/section/int:section_id>/edit/', views.update_section, name='update_chapter'),
    path('unite/<int:unite_id>/section/int:section_id>/view/', views.view_section, name='update_chapter'),
    path('section/<int:unite_id>/edit/', views.delete_section, name='update_chapter'),

    path('unite/<int:unite_id>/sections/creer/', views.create_section, name='create_section'),
    path('unite/<int:unite_id>/section/<int:section_id>/', views.view_section, name='view_section'),
    path('section/<int:section_id>/modifier/', views.update_section, name='update_section'),
    path('section/<int:section_id>/supprimer/', views.delete_section, name='delete_section'),

]


urlpatterns += [
    # Heading search
    path('heading-search/', views.heading_comparative_search, name='heading_search'),
    path('api/heading-search/', views.heading_search_api, name='api_heading_search'),
    
    # Content search
    path('content-search/', views.content_comparative_search, name='content_search'),
    path('api/content-search/', views.content_search_api_grouped, name='api_content_search'),
    
    # Shared AJAX endpoints
    path('ajax/get-unites-by-level/', views.ajax_get_unites_by_level, name='ajax_unites'),
    path('api/download-pdf/', views.download_results_pdf, name='download_pdf'),
    path('api/download-content-pdf/', views.download_results_pdf, name='download_content_pdf'),
]

urlpatterns += [
    # Student URLs
    path('subjects/', views_student.subject_list, name='subject_list_student'),
    path('subject/<int:pk>/', views_student.subject_detail, name='subject_detail_student'),
    path('subject/<int:subject_pk>/chapter/<int:chapter_pk>/', views_student.chapter_detail, name='chapter_detail_student'),
]


urlpatterns += [
    path('ue_list/', views.ue_list, name="ue_list"),
    path('<int:ue_id>/chapter_list/', views.chapter_list_view, name="chapter_list"),
    path('<int:ue_id>/chapter_element/', views.chapter_element, name="chapter_element"),
]

