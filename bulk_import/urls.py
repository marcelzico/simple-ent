from django.urls import path
from . import views

app_name = 'bulk_import'

urlpatterns = [
    # Dashboard / overview
    path('', views.dashboard, name='dashboard'),

    # Level based navigation
    path('levels/', views.level_list, name='level_list'),
    path('levels/<str:level_name>/unites/', views.unite_list, name='unite_list'),
    path('unites/<int:unite_id>/chapters/', views.chapter_list, name='chapter_list'),

    # Single item imports (from earlier)
    path('level/<str:level_name>/import/', views.import_level_unites, name='import_level_unites'),
    path('unite/<int:unite_id>/import-chapters/', views.import_unite_chapters, name='import_unite_chapters'),
    path('chapter/<int:chapter_id>/import-copies/', views.import_chapter_copies, name='import_chapter_copies'),
    path('chapter/<int:chapter_id>/import-exercises/', views.import_chapter_exercises, name='import_chapter_exercises'),

    # Bulk imports (POST only)
    path('bulk/import-unites/', views.bulk_import_unites, name='bulk_import_unites'),
    path('bulk/import-chapters/', views.bulk_import_chapters, name='bulk_import_chapters'),
    path('bulk/import-copies/', views.bulk_import_copies, name='bulk_import_copies'),
    path('bulk/import-exercises/', views.bulk_import_exercises, name='bulk_import_exercises'),
    path('bulk/generate-exercises/', views.generate_chapter_exercise_files, name='generate_chapter_exercise_files'),
]