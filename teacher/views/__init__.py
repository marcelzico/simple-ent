# teacher/views/__init__.py
from .dashboard import dashboard_view
from .unites import (
    unites_list, unite_create, unite_edit, unite_delete,
    unite_teachers_manage
)
from .chapitres import (
    chapitres_list, chapitre_create, chapitre_edit, chapitre_delete, chapitre_reorder
)
from .mcq_views import (
    mcq_list, mcq_create, mcq_edit, mcq_delete
)
from .qa_views import (
    qa_list, qa_create, qa_edit, qa_delete
)
from .tf_views import (
    tf_list, tf_create, tf_edit, tf_delete
)
from .quiz_composite_views import (
    mcq_quiz_list, mcq_quiz_create, mcq_quiz_edit, mcq_quiz_delete,
    qa_quiz_list, qa_quiz_create, qa_quiz_edit, qa_quiz_delete
)
from .flashcard_views import (
    flashcard_sets_list, flashcard_set_create, flashcard_set_edit, flashcard_set_delete,
    flashcard_cards_list, flashcard_card_create, flashcard_card_edit, flashcard_card_delete
)
from .cas_clinique_views import (
    cas_liste, cas_creer, cas_modifier, cas_supprimer, cas_detail,
    cas_qcm_creer, cas_qr_creer, cas_vf_creer,
    cas_qcm_modifier, cas_qr_modifier, cas_vf_modifier,
    cas_qcm_supprimer, cas_qr_supprimer, cas_vf_supprimer
)
from .etudiant_views import (
    etudiants_liste, etudiant_detail, etudiant_resultats, etudiant_progression
)
from .profil_views import (
    profil_index, profil_notifications, profil_notification_update, profil_modifier, 
    profil_changer_mot_de_passe,
)