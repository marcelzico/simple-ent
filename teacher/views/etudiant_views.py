from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, QAResult, TrueFalseResult, MCQAttempt, QAAttempt
from clinical_case_simple.models import ExamAttempt
from utilisateur.models import User
from student.models import StudentProfile
from ..decorators import teacher_required
from ..utils import TeacherStats


@login_required
@teacher_required
def etudiants_liste(request):
    """
    Liste des étudiants inscrits dans les unités enseignées
    (basée sur la correspondance de niveau)
    """
    teacher = request.user
    
    # Récupérer les unités enseignées et leurs niveaux
    teaching_unites = Unite.objects.filter(teachers=teacher)
    levels = [unite.level for unite in teaching_unites if unite.level]
    
    if not levels:
        context = {
            'page_obj': [],
            'etudiants': [],
            'teaching_unites': teaching_unites,
            'selected_unite': None,
            'search_query': '',
            'total_etudiants': 0,
        }
        return render(request, 'teacher/etudiants/liste.html', context)
    
    # Récupérer les étudiants dont le niveau correspond
    student_profiles = StudentProfile.objects.filter(
        level__in=levels,
        user__is_student=True,
        is_active_student=True
    ).select_related('user')
    
    etudiants = User.objects.filter(
        id__in=student_profiles.values_list('user_id', flat=True),
        is_student=True
    )
    
    # Filtrer par recherche
    search_query = request.GET.get('q')
    if search_query:
        etudiants = etudiants.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(student_profile__student_id_number__icontains=search_query)
        )
    
    # Filtrer par unité spécifique (via son niveau)
    unite_filter = request.GET.get('unite')
    selected_unite = None
    if unite_filter:
        selected_unite = get_object_or_404(Unite, pk=unite_filter)
        if selected_unite in teaching_unites and selected_unite.level:
            # Filtrer les étudiants par le niveau de cette unité
            etudiants = etudiants.filter(student_profile__level=selected_unite.level)
    
    # Ajouter les statistiques pour chaque étudiant
    for etudiant in etudiants:
        # Récupérer le niveau de l'étudiant
        student_profile = getattr(etudiant, 'student_profile', None)
        etudiant.student_level = student_profile.level if student_profile else '-'
        
        # Calculer les scores moyens
        etudiant.mcq_avg = _get_student_avg_score(etudiant, MCQResult)
        etudiant.qa_avg = _get_student_avg_score(etudiant, QAResult)
        etudiant.tf_avg = _get_student_avg_score(etudiant, TrueFalseResult)
        
        # Calculer la moyenne globale
        scores = [s for s in [etudiant.mcq_avg, etudiant.qa_avg, etudiant.tf_avg] if s > 0]
        etudiant.global_avg = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Dernière activité
        etudiant.last_activity = _get_last_activity(etudiant)
    
    # Pagination
    paginator = Paginator(etudiants, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'etudiants': page_obj,
        'teaching_unites': teaching_unites,
        'selected_unite': selected_unite,
        'search_query': search_query,
        'total_etudiants': etudiants.count(),
    }
    
    return render(request, 'teacher/etudiants/liste.html', context)


def _get_student_avg_score(student, result_model):
    """Calcule la moyenne d'un étudiant pour un type de quiz"""
    result = result_model.objects.filter(
        student=student
    ).aggregate(avg=Avg('score'))
    return round(result['avg'], 1) if result['avg'] else 0


def _get_last_activity(student):
    """Récupère la dernière activité de l'étudiant"""
    last_dates = []
    
    for result_model in [MCQResult, QAResult, TrueFalseResult]:
        last = result_model.objects.filter(
            student=student
        ).order_by('-created_at').first()
        if last:
            last_dates.append(last.created_at)
    
    if last_dates:
        return max(last_dates)
    return None


@login_required
@teacher_required
def etudiant_detail(request, pk):
    """
    Détail complet d'un étudiant (progression, résultats, etc.)
    """
    etudiant = get_object_or_404(User, pk=pk, is_student=True)
    teacher = request.user
    
    # Récupérer le niveau de l'étudiant
    student_profile = getattr(etudiant, 'student_profile', None)
    student_level = student_profile.level if student_profile else None
    
    if not student_level:
        messages.warning(request, "Cet étudiant n'a pas de niveau défini.")
        return redirect('teacher:etudiants_liste')
    
    # Récupérer les unités enseignées par le teacher qui correspondent au niveau de l'étudiant
    teaching_unites = Unite.objects.filter(teachers=teacher, level=student_level)
    
    if not teaching_unites.exists():
        messages.warning(request, "Aucune unité ne correspond au niveau de cet étudiant.")
        return redirect('teacher:etudiants_liste')
    
    # Récupérer les chapitres des unités concernées
    chapters = Chapter.objects.filter(ue__in=teaching_unites, is_active=True)
    
    # Récupérer les résultats par chapitre
    chapter_results = []
    for chapter in chapters:
        mcq_score = MCQResult.objects.filter(
            student=etudiant,
            chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        qa_score = QAResult.objects.filter(
            student=etudiant,
            chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        tf_score = TrueFalseResult.objects.filter(
            student=etudiant,
            chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        has_studied = any([
            MCQResult.objects.filter(student=etudiant, chapter=chapter).exists(),
            QAResult.objects.filter(student=etudiant, chapter=chapter).exists(),
            TrueFalseResult.objects.filter(student=etudiant, chapter=chapter).exists(),
        ])
        
        # Score global du chapitre
        scores = [s for s in [mcq_score, qa_score, tf_score] if s > 0]
        global_score = round(sum(scores) / len(scores), 1) if scores else 0
        
        chapter_results.append({
            'chapter': chapter,
            'mcq_score': round(mcq_score, 1),
            'qa_score': round(qa_score, 1),
            'tf_score': round(tf_score, 1),
            'global_score': global_score,
            'has_studied': has_studied,
        })
    
    # Statistiques globales
    stats = TeacherStats(teacher)
    
    # Récupérer les tentatives de quiz composites
    mcq_attempts = MCQAttempt.objects.filter(
        student=etudiant,
        quiz__subject__in=teaching_unites
    ).select_related('quiz')[:10]
    
    qa_attempts = QAAttempt.objects.filter(
        student=etudiant,
        quiz__subject__in=teaching_unites
    ).select_related('quiz')[:10]
    
    # Récupérer les tentatives de cas cliniques
    exam_attempts = ExamAttempt.objects.filter(
        student=etudiant,
        enonce__unite_associee__in=teaching_unites
    ).select_related('enonce')[:10]
    
    # Évolution des performances
    weekly_scores = _get_weekly_scores(etudiant, chapters)
    
    context = {
        'etudiant': etudiant,
        'student_profile': student_profile,
        'chapter_results': chapter_results,
        'mcq_attempts': mcq_attempts,
        'qa_attempts': qa_attempts,
        'exam_attempts': exam_attempts,
        'total_chapters': chapters.count(),
        'studied_chapters': sum(1 for cr in chapter_results if cr['has_studied']),
        'teaching_unites': teaching_unites,
        'weekly_scores': weekly_scores,
    }
    
    return render(request, 'teacher/etudiants/detail.html', context)


def _get_weekly_scores(student, chapters):
    """
    Récupère les scores hebdomadaires des 7 dernières semaines
    """
    import json
    
    weeks = []
    scores = []
    
    end_date = timezone.now()
    
    for i in range(7):
        week_start = end_date - timedelta(weeks=i+1)
        week_end = end_date - timedelta(weeks=i)
        
        week_label = f"S{8-i}" if i < 7 else f"S-{i}"
        weeks.append(week_label)
        
        # Calculer la moyenne de la semaine
        week_scores = []
        
        for result_model in [MCQResult, QAResult, TrueFalseResult]:
            avg = result_model.objects.filter(
                student=student,
                chapter__in=chapters,
                created_at__gte=week_start,
                created_at__lt=week_end
            ).aggregate(avg=Avg('score'))['avg']
            if avg:
                week_scores.append(avg)
        
        if week_scores:
            scores.append(round(sum(week_scores) / len(week_scores), 1))
        else:
            scores.append(0)
    
    # Inverser pour avoir l'ordre chronologique
    weeks.reverse()
    scores.reverse()
    
    return {
        'weeks': json.dumps(weeks),
        'scores': json.dumps(scores),
    }


@login_required
@teacher_required
def etudiant_resultats(request, pk, type_quiz='all'):
    """
    Résultats détaillés d'un étudiant par type de quiz
    """
    etudiant = get_object_or_404(User, pk=pk, is_student=True)
    teacher = request.user
    
    # Récupérer le niveau de l'étudiant
    student_profile = getattr(etudiant, 'student_profile', None)
    student_level = student_profile.level if student_profile else None
    
    if not student_level:
        messages.warning(request, "Cet étudiant n'a pas de niveau défini.")
        return redirect('teacher:etudiants_liste')
    
    # Récupérer les unités du teacher qui correspondent au niveau
    teaching_unites = Unite.objects.filter(teachers=teacher, level=student_level)
    chapters = Chapter.objects.filter(ue__in=teaching_unites)
    
    if type_quiz == 'mcq':
        results = MCQResult.objects.filter(
            student=etudiant,
            chapter__in=chapters
        ).select_related('chapter', 'chapter__ue').order_by('-created_at')
        title = "Résultats QCM"
    elif type_quiz == 'qa':
        results = QAResult.objects.filter(
            student=etudiant,
            chapter__in=chapters
        ).select_related('chapter', 'chapter__ue').order_by('-created_at')
        title = "Résultats Questions/Réponses"
    elif type_quiz == 'tf':
        results = TrueFalseResult.objects.filter(
            student=etudiant,
            chapter__in=chapters
        ).select_related('chapter', 'chapter__ue').order_by('-created_at')
        title = "Résultats Vrai/Faux"
    else:
        # Tous les résultats combinés
        all_results = []
        for res in MCQResult.objects.filter(student=etudiant, chapter__in=chapters):
            all_results.append({
                'id': res.id,
                'score': res.score,
                'created_at': res.created_at,
                'chapter_title': res.chapter.title,
                'ue_title': res.chapter.ue.title,
                'type': 'QCM'
            })
        for res in QAResult.objects.filter(student=etudiant, chapter__in=chapters):
            all_results.append({
                'id': res.id,
                'score': res.score,
                'created_at': res.created_at,
                'chapter_title': res.chapter.title,
                'ue_title': res.chapter.ue.title,
                'type': 'Question/Réponse'
            })
        for res in TrueFalseResult.objects.filter(student=etudiant, chapter__in=chapters):
            all_results.append({
                'id': res.id,
                'score': res.score,
                'created_at': res.created_at,
                'chapter_title': res.chapter.title,
                'ue_title': res.chapter.ue.title,
                'type': 'Vrai/Faux'
            })
        all_results.sort(key=lambda x: x['created_at'], reverse=True)
        results = all_results
        title = "Tous les résultats"
        type_quiz = 'all'
    
    # Pagination
    paginator = Paginator(results, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiques
    avg_score = 0
    if type_quiz != 'all' and hasattr(results, 'aggregate'):
        avg_score = results.aggregate(avg=Avg('score'))['avg'] or 0
    
    context = {
        'page_obj': page_obj,
        'results': page_obj,
        'etudiant': etudiant,
        'type_quiz': type_quiz,
        'title': title,
        'avg_score': round(avg_score, 1) if avg_score else 0,
        'total_results': len(results) if isinstance(results, list) else results.count(),
    }
    
    return render(request, 'teacher/etudiants/resultats.html', context)


@login_required
@teacher_required
def etudiant_progression(request, pk, unite_id):
    """
    Progression d'un étudiant dans une unité spécifique
    """
    etudiant = get_object_or_404(User, pk=pk, is_student=True)
    unite = get_object_or_404(Unite, pk=unite_id)
    teacher = request.user
    
    # Vérifier que l'enseignant a accès à cette unité
    if not unite.is_teacher(teacher) and not teacher.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à cette unité.')
        return redirect('teacher:etudiants_liste')
    
    # Vérifier que le niveau de l'étudiant correspond à l'unité
    student_profile = getattr(etudiant, 'student_profile', None)
    if not student_profile or student_profile.level != unite.level:
        messages.warning(request, f"Cet étudiant n'est pas au niveau {unite.get_level_display()}")
        return redirect('teacher:etudiant_detail', pk=etudiant.id)
    
    chapters = Chapter.objects.filter(ue=unite, is_active=True).order_by('order')
    
    progression_data = []
    for chapter in chapters:
        mcq_score = MCQResult.objects.filter(
            student=etudiant, chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        qa_score = QAResult.objects.filter(
            student=etudiant, chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        tf_score = TrueFalseResult.objects.filter(
            student=etudiant, chapter=chapter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        # Score global du chapitre
        scores = [s for s in [mcq_score, qa_score, tf_score] if s > 0]
        global_score = round(sum(scores) / len(scores), 1) if scores else 0
        
        # Temps d'étude (si StudySession existe)
        try:
            from lecon.models import StudySession
            total_time = StudySession.objects.filter(
                student=etudiant,
                chapter=chapter
            ).aggregate(total=Sum('duration_seconds'))['total'] or 0
            total_time_minutes = total_time // 60
        except ImportError:
            total_time_minutes = 0
        
        progression_data.append({
            'chapter': chapter,
            'mcq_score': round(mcq_score, 1),
            'qa_score': round(qa_score, 1),
            'tf_score': round(tf_score, 1),
            'global_score': global_score,
            'study_time': total_time_minutes,
            'has_studied': mcq_score > 0 or qa_score > 0 or tf_score > 0,
        })
    
    # Score global de l'unité
    global_scores = [p['global_score'] for p in progression_data if p['global_score'] > 0]
    unite_global_score = round(sum(global_scores) / len(global_scores), 1) if global_scores else 0
    
    context = {
        'etudiant': etudiant,
        'unite': unite,
        'progression_data': progression_data,
        'unite_global_score': unite_global_score,
        'chapters_completed': sum(1 for p in progression_data if p['has_studied']),
        'total_chapters': len(chapters),
    }
    
    return render(request, 'teacher/etudiants/progression.html', context)

