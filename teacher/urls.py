from django.urls import path
from . import views

app_name = 'teacher'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_view, name='dashboard'),
    
    # ==================== UNITÉS ====================
    path('unites/', views.unites_list, name='unites_list'),
    path('unites/creer/', views.unite_create, name='unite_create'),
    path('unites/<int:pk>/modifier/', views.unite_edit, name='unite_edit'),
    path('unites/<int:pk>/supprimer/', views.unite_delete, name='unite_delete'),
    path('unites/<int:pk>/enseignants/', views.unite_teachers_manage, name='unite_teachers_manage'),
    
    # ==================== CHAPITRES ====================
    path('unites/<int:unite_id>/chapitres/', views.chapitres_list, name='chapitres_list'),
    path('unites/<int:unite_id>/chapitres/creer/', views.chapitre_create, name='chapitre_create'),
    path('chapitres/<int:pk>/modifier/', views.chapitre_edit, name='chapitre_edit'),
    path('chapitres/<int:pk>/supprimer/', views.chapitre_delete, name='chapitre_delete'),
    path('chapitres/<int:unite_id>/reordonner/', views.chapitre_reorder, name='chapitre_reorder'),
    
    # ==================== QCM ====================
    path('qcm/', views.mcq_list, name='mcq_list'),
    path('unites/<int:unite_id>/qcm/', views.mcq_list, name='mcq_list_by_unite'),
    path('chapitres/<int:chapter_id>/qcm/creer/', views.mcq_create, name='mcq_create'),
    path('qcm/<int:pk>/modifier/', views.mcq_edit, name='mcq_edit'),
    path('qcm/<int:pk>/supprimer/', views.mcq_delete, name='mcq_delete'),
    
    # ==================== QUESTIONS/RÉPONSES ====================
    path('qa/', views.qa_list, name='qa_list'),
    path('unites/<int:unite_id>/qa/', views.qa_list, name='qa_list_by_unite'),
    path('chapitres/<int:chapter_id>/qa/creer/', views.qa_create, name='qa_create'),
    path('qa/<int:pk>/modifier/', views.qa_edit, name='qa_edit'),
    path('qa/<int:pk>/supprimer/', views.qa_delete, name='qa_delete'),
    
    # ==================== VRAI/FAUX ====================
    path('tf/', views.tf_list, name='tf_list'),
    path('unites/<int:unite_id>/tf/', views.tf_list, name='tf_list_by_unite'),
    path('chapitres/<int:chapter_id>/tf/creer/', views.tf_create, name='tf_create'),
    path('tf/<int:pk>/modifier/', views.tf_edit, name='tf_edit'),
    path('tf/<int:pk>/supprimer/', views.tf_delete, name='tf_delete'),
    
    # ==================== QUIZ COMPOSITES ====================
    # CORRECTION: URL avec paramètre optionnel (int:unite_id peut être vide)
    # Note: Django ne supporte pas nativement les paramètres optionnels dans path()
    # On utilise donc deux URLs distinctes
    
    # MCQ Quiz - Liste sans filtre
    path('quiz/mcq/', views.mcq_quiz_list, name='mcq_quiz_list'),
    # MCQ Quiz - Liste filtrée par unité
    path('quiz/mcq/unite/<int:unite_id>/', views.mcq_quiz_list, name='mcq_quiz_list_by_unite'),
    
    # MCQ Quiz - CRUD
    path('unites/<int:unite_id>/quiz/mcq/creer/', views.mcq_quiz_create, name='mcq_quiz_create'),
    path('quiz/mcq/<int:pk>/modifier/', views.mcq_quiz_edit, name='mcq_quiz_edit'),
    path('quiz/mcq/<int:pk>/supprimer/', views.mcq_quiz_delete, name='mcq_quiz_delete'),
    
    # QA Quiz - Liste sans filtre
    path('quiz/qa/', views.qa_quiz_list, name='qa_quiz_list'),
    # QA Quiz - Liste filtrée par unité
    path('quiz/qa/unite/<int:unite_id>/', views.qa_quiz_list, name='qa_quiz_list_by_unite'),
    
    # QA Quiz - CRUD
    path('unites/<int:unite_id>/quiz/qa/creer/', views.qa_quiz_create, name='qa_quiz_create'),
    path('quiz/qa/<int:pk>/modifier/', views.qa_quiz_edit, name='qa_quiz_edit'),
    path('quiz/qa/<int:pk>/supprimer/', views.qa_quiz_delete, name='qa_quiz_delete'),
    
    # ==================== FLASHCARDS ====================
    path('flashcards/', views.flashcard_sets_list, name='flashcard_sets'),
    path('unites/<int:unite_id>/flashcards/creer/', views.flashcard_set_create, name='flashcard_set_create'),
    path('flashcards/<int:pk>/modifier/', views.flashcard_set_edit, name='flashcard_set_edit'),
    path('flashcards/<int:pk>/supprimer/', views.flashcard_set_delete, name='flashcard_set_delete'),
    path('flashcards/set/<int:set_id>/cartes/', views.flashcard_cards_list, name='flashcard_cards'),
    path('flashcards/set/<int:set_id>/cartes/creer/', views.flashcard_card_create, name='flashcard_card_create'),
    path('flashcards/carte/<int:pk>/modifier/', views.flashcard_card_edit, name='flashcard_card_edit'),
    path('flashcards/carte/<int:pk>/supprimer/', views.flashcard_card_delete, name='flashcard_card_delete'),
    
    # ==================== CAS CLINIQUES ====================
    path('cas/', views.cas_liste, name='cas_liste'),
    path('unites/<int:unite_id>/cas/creer/', views.cas_creer, name='cas_creer'),
    path('cas/creer/', views.cas_creer, name='cas_creer_sans_unite'),
    path('cas/<int:pk>/', views.cas_detail, name='cas_detail'),
    path('cas/<int:pk>/modifier/', views.cas_modifier, name='cas_modifier'),
    path('cas/<int:pk>/supprimer/', views.cas_supprimer, name='cas_supprimer'),
    
    # Questions des cas cliniques - QCM
    path('cas/<int:cas_pk>/qcm/creer/', views.cas_qcm_creer, name='cas_qcm_creer'),
    path('cas/qcm/<int:pk>/modifier/', views.cas_qcm_modifier, name='cas_qcm_modifier'),
    path('cas/qcm/<int:pk>/supprimer/', views.cas_qcm_supprimer, name='cas_qcm_supprimer'),
    
    # Questions des cas cliniques - QR
    path('cas/<int:cas_pk>/qr/creer/', views.cas_qr_creer, name='cas_qr_creer'),
    path('cas/qr/<int:pk>/modifier/', views.cas_qr_modifier, name='cas_qr_modifier'),
    path('cas/qr/<int:pk>/supprimer/', views.cas_qr_supprimer, name='cas_qr_supprimer'),
    
    # Questions des cas cliniques - VF
    path('cas/<int:cas_pk>/vf/creer/', views.cas_vf_creer, name='cas_vf_creer'),
    path('cas/vf/<int:pk>/modifier/', views.cas_vf_modifier, name='cas_vf_modifier'),
    path('cas/vf/<int:pk>/supprimer/', views.cas_vf_supprimer, name='cas_vf_supprimer'),
    
    # ==================== ÉTUDIANTS ====================
    path('etudiants/', views.etudiants_liste, name='etudiants_liste'),
    path('etudiants/<int:pk>/', views.etudiant_detail, name='etudiant_detail'),
    path('etudiants/<int:pk>/resultats/<str:type_quiz>/', views.etudiant_resultats, name='etudiant_resultats'),
    path('etudiants/<int:pk>/resultats/', views.etudiant_resultats, name='etudiant_resultats_all'),
    path('etudiants/<int:pk>/progression/<int:unite_id>/', views.etudiant_progression, name='etudiant_progression'),
    
    # ==================== PROFIL ====================
    path('profil/', views.profil_index, name='profil_index'),
    path('profil/modifier/', views.profil_modifier, name='profil_modifier'),
    path('profil/mot-de-passe/', views.profil_changer_mot_de_passe, name='profil_changer_mdp'),
    path('profil/notifications/', views.profil_notifications, name='profil_notifications'),
    path('profil/notifications/<str:notif_type>/toggle/', views.profil_notification_update, name='profil_notification_toggle'),
]