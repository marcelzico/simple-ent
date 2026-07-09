from django.urls import path
from . import views, views_student, bulk_elements_views, bulk_import_views, new_bulk_import_path_views

app_name = 'lessoncopy'

urlpatterns = [
    path('chapter/<int:chapter_id>/copy/create/', views.copy_create, name='copy_create'),
    path('copy/<int:pk>/edit/', views.CopyUpdateView.as_view(), name='copy_edit'),
    path('<int:unite_id>/chapters/<int:chapter_id>/lesson/', views.copy_view, name='lesson'),
    path('chapters/<int:chapter_id>/modify/<int:copy_id>/', views.modify_copy, name='modify'),
    path('chapters/<int:chapter_id>/delete/<int:copy_id>/', views.delete_copy, name='delete'),
    path('chapter/<int:chapter_id>/create-resume-ia/', views.create_resume_ia, name='create-resume-ia'),

    # AI Resume URLs
    path('ai-resume/<int:resume_id>/edit/', views.edit_ai_resume, name='edit_ai_resume'),
    path('ai-resume/<int:resume_id>/delete/', views.delete_ai_resume, name='delete_ai_resume'),
    
    # Document URLs
    # path('chapter/<int:chapter_id>/upload/', views.upload_document, name="chapter-upload-document"),
    # path('document/<int:document_id>/edit/', views.edit_document, name='edit_document'),
    # path('document/<int:document_id>/delete/', views.delete_document, name='delete_document'),
    # path('chapter/<int:chapter_id>/documents/delete-all/', views.delete_all_documents, name='delete_all_documents'),
    
    # Content Management URLs
    path('chapter/<int:chapter_id>/content/delete-all/', views.delete_all_content, name='delete_all_content'),
]

urlpatterns += [
    path('ue/<int:unite_id>/chapitre/<int:chapter_id>/leçon', views_student.chapter_copies_view, name='lesson_student'),

    path('chapter/<int:chapter_id>/resume/create/', views_student.create_resume, name='create_resume'),
    path('chapter/<int:resume_id>/resume/edit/', views_student.edit_resume, name='edit_resume'),
    path('chapter/<int:chapter_id>/resume/delete/', views_student.delete_resume, name='delete_resume'),
    path('chapter/<int:chapter_id>/resume/view/', views_student.view_my_resumes, name='view_my_resume'),

    path('chapter/<int:copy_id>/notes/add/', views_student.add_user_annotation, name='annotation_add'),
    path('chapter/notes/edit/', views_student.update_annotation, name='annotation_edit'),
    # path('chapter/<int:chapter_id>/notes/view/', views_student.get_annotations, name='annotation_view'),
    path('chapter/notes/delete/', views_student.delete_annotation, name='annotation_delete'),

    path('chapter/<int:chapter_id>/study_stats/', views_student.study_stats, name='study_stats'),

    # Study session URLs
    path('study-session/start/', views_student.start_study_session, name='start_study_session'),
    path('study-session/end/', views_student.end_study_session, name='end_study_session'),
    
    # Simple annotation URLs
    path('save-simple-annotation/', views_student.save_simple_annotation, name='save_simple_annotation'),
    path('delete-simple-annotation/', views_student.delete_simple_annotation, name='delete_simple_annotation'),
    path('get-copy-annotation/<int:copy_id>/', views_student.get_copy_annotation, name='get_copy_annotation'),
    path('get-annotations/<int:chapter_id>/', views_student.get_annotations, name='get_annotations'),

]

urlpatterns += [
    # Document URLs - IMPORTANT: Add these
    path('chapter/<int:chapter_id>/upload/', views.upload_document, name="chapter-upload-document"),
    path('document/<int:document_id>/', views.view_document, name='view_document'),
    path('document/<int:document_id>/pdf-data/', views.get_pdf_data, name='get_pdf_data'),
    path('document/<int:document_id>/search/', views.search_pdf, name='search_pdf'),
    path('document/<int:document_id>/edit/', views.edit_document, name='edit_document'),
    path('document/<int:document_id>/delete/', views.delete_document, name='delete_document'),
    path('chapter/<int:chapter_id>/documents/delete-all/', views.delete_all_documents, name='delete_all_documents'),

    # bulk import for all type of quizzes and cards
    path('chapter/<int:chapter_id>/bulk-upload/', bulk_elements_views.bulk_upload_chapter, name='bulk_upload_chapter'),
]

 
urlpatterns += [
    path('bulk-import-folder/', bulk_import_views.bulk_import_chapters_from_folder, name='bulk_import_folder'),
    path('bulk-import/chapter-data-path/', new_bulk_import_path_views.bulk_import_chapter_data, name='bulk_import_chapter_data_path'),
]
