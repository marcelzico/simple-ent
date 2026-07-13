from django.urls import path
from . import views_mcq, views_qa, views_tf, views_student

app_name = 'quizzes'

urlpatterns = [
# -----------------------------MCQ AND MCQ QUIZ ----------------------------
    # path('mcq-results/', views_mcq.mcq_results, name='mcq_results'),
    path('mcq/upload-csv/<int:chapter_id>/', views_mcq.upload_csv_mcq, name='upload_csv_mcq'),
    path('mcq/create/<int:chapter_pk>/', views_mcq.create_mcq, name='create_mcq'),
    path('chapter/<int:chapter_id>/mcqs/delete-all/', views_mcq.delete_all_mcqs, name='delete_all_mcqs'),
    path('mcq/update/<int:mcq_id>/', views_mcq.update_mcq, name='update_mcq'),
    path('mcq/delete/<int:mcq_id>/', views_mcq.delete_mcq, name='delete_mcq'),
    path('mcq/bulk-actions/<int:chapter_id>/', views_mcq.mcq_bulk_actions, name='mcq_bulk_actions'),
    path('mcq/view/<int:chapter_id>/', views_mcq.view_mcqs, name='view_mcqs'),
    
    path('create-mcq-quiz/<int:subject_pk>/', views_mcq.create_mcq_quiz, name='create_mcq_quiz'),
    path('mcq-quiz/<int:quiz_id>/edit/', views_mcq.edit_mcq_quiz, name='edit_mcq_quiz'),
    path('mcq-quiz/<int:quiz_id>/delete/', views_mcq.delete_mcq_quiz, name='delete_mcq_quiz'),
    path('mcq-quizzes/', views_mcq.list_mcq_quizzes, name='list_mcq_quizzes'),
    path('mcq-quizzes/<int:subject_pk>/', views_mcq.list_subject_mcq_quizzes, name='list_subject_mcq_quizzes'),
    path('mcq-quiz/<int:quiz_id>/detail/', views_mcq.mcq_quiz_detail, name='mcq_quiz_detail'),
    # path('mcq-quiz-results/', views_mcq.mcq_quiz_results, name='mcq_quiz_results'),

    # AJAX endpoints (existing)
    path('ajax/load-questions/', views_mcq.load_questions_ajax, name='load_questions_ajax'),


# ------------------------- QA AND QA QUZ -----------------------------------
    # path('qa-results/', views_qa.qa_results, name='qa_results'),
    # path('qa/upload-csv/<int:chapter_id>/', views_qa.upload_csv_qa, name='upload_csv_qa'),
    # path('qa/create/<int:chapter_pk>/', views_qa.create_qa, name='create_qa'),
    # path('chapter/<int:chapter_id>/qas/delete-all/', views_qa.delete_all_qas, name='delete_all_qas'),
    # path('qa/update/<int:qa_id>/', views_qa.update_qa, name='update_qa'),
    # path('qa/delete/<int:qa_id>/', views_qa.delete_qa, name='delete_qa'),
    # path('qa/bulk-actions/<int:chapter_id>/', views_qa.qa_bulk_actions, name='qa_bulk_actions'),
    # path('qa/view/<int:chapter_id>/', views_qa.view_qas, name='view_qas'),
    
    # path('qa-quizzes/', views_qa.list_qa_quizzes, name='list_qa_quizzes'),
    # path('qa-quizzes/<int:subject_pk>/', views_qa.list_qa_quizzes, name='list_subject_qa_quizzes'),
    # path('qa-quiz/<int:quiz_id>/detail/', views_qa.qa_quiz_detail, name='qa_quiz_detail'),
    # path('qa-quiz/<int:quiz_id>/edit/', views_qa.edit_qa_quiz, name='edit_qa_quiz'),
    # path('qa-quiz/<int:quiz_id>/delete/', views_qa.delete_qa_quiz, name='delete_qa_quiz'),
    # path('create-qa-quiz/<int:subject_pk>/', views_qa.create_qa_quiz, name='create_qa_quiz'),
    # path('qa-quiz-results/', views_qa.qa_quiz_results, name='qa_quiz_results'),

    # path('ajax/load-qa-questions/', views_qa.load_qa_questions_ajax, name='load_qa_questions_ajax'),


# ------------------------------ TRUE OR FALSE ------------------------------------
    # path('tf-results/', views_tf.tf_results, name='tf_results'),
    path('tf/upload-csv/<int:chapter_id>/', views_tf.upload_csv_tf, name='upload_csv_tf'),
    path('chapter/<int:chapter_id>/tfs/delete-all/', views_tf.delete_all_tfs, name='delete_all_tfs'),
    path('tf/update/<int:tf_id>/', views_tf.update_tf, name='update_tf'),
    path('tf/delete/<int:tf_id>/', views_tf.delete_tf, name='delete_tf'),
    path('tf/bulk-actions/<int:chapter_id>/', views_tf.tf_bulk_actions, name='tf_bulk_actions'),
    path('tf/view/<int:chapter_id>/', views_tf.view_tfs, name='view_tfs'),


    path('mcq/<int:chapter_id>/start', views_student.start_mcq, name='start_mcq'),
    path('mcq/<int:chapter_id>/submit', views_student.submit_mcq, name='submit_mcq'),
    path('mcq-results/', views_student.mcq_results, name='mcq_results'),

    path('mcq-quiz/<int:quiz_id>/', views_student.start_mcq_quiz, name='start_mcq_quiz'),
    path('mcq-attempt/<int:attempt_id>/submit/', views_student.submit_mcq_quiz, name='submit_mcq_quiz'),
    path('mcq-quiz-results/', views_student.mcq_quiz_results, name='mcq_quiz_results'),
    
    # path('qa/<int:chapter_id>/start_qa/', views_student.start_qa, name="start_qa"),
    # path('qa/<int:chapter_id>/submit_qa/', views_student.submit_qa, name="submit_qa"),
    # path('qa-results/', views_student.qa_results, name='qa_results'),

    # path('qa-quiz/<int:quiz_id>/', views_student.start_qa_quiz, name='start_qa_quiz'),
    # path('qa-attempt/<int:attempt_id>/submit/', views_student.submit_qa_quiz, name='submit_qa_quiz'),
    # path('qa-quiz-results/', views_student.qa_quiz_results, name='qa_quiz_results'),

    path('tf/<int:chapter_id>/start-tf/', views_student.start_tf, name='start_tf'),
    path('tf/<int:chapter_id>/submit_tf/', views_student.submit_tf, name="submit_tf"),
    path('tf-results/', views_student.tf_results, name='tf_results'),

]
