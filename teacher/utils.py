from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from lecon.models import Unite, Chapter
from quizzes.models import MCQResult, QAResult, TrueFalseResult, MCQAttempt, QAAttempt
from django.contrib.auth import get_user_model
from student.models import StudentProfile
# from clinical_case_simple.models import ExamAttempt

User = get_user_model()


class TeacherStats:
    """Classe utilitaire pour les statistiques des enseignants"""
    
    def __init__(self, teacher, unite=None):
        self.teacher = teacher
        self.unite = unite
        self._cache = {}
    
    def get_teaching_unites(self):
        """Récupère les unités enseignées"""
        if self.unite:
            return [self.unite]
        return list(Unite.objects.filter(teachers=self.teacher))
    
    def get_students(self):
        """
        Récupère les étudiants inscrits aux unités enseignées
        via la correspondance de niveau (level)
        """
        unites = self.get_teaching_unites()
        if not unites:
            return User.objects.none()
        
        # Récupérer les niveaux des unités enseignées
        levels = [unite.level for unite in unites if unite.level]
        
        if not levels:
            return User.objects.none()
        
        # Récupérer les étudiants dont le niveau correspond
        student_profiles = StudentProfile.objects.filter(
            level__in=levels,
            user__is_student=True,
            is_active_student=True
        ).select_related('user')
        
        # Récupérer les utilisateurs
        student_ids = student_profiles.values_list('user_id', flat=True).distinct()
        
        return User.objects.filter(id__in=student_ids, is_student=True)
    
    def get_students_count(self):
        """Nombre d'étudiants dans les unités enseignées"""
        cache_key = 'students_count'
        if cache_key not in self._cache:
            self._cache[cache_key] = self.get_students().count()
        return self._cache[cache_key]
    
    def get_mcq_count(self):
        """Nombre de QCM créés par l'enseignant"""
        from quizzes.models import MCQ
        cache_key = 'mcq_count'
        if cache_key not in self._cache:
            self._cache[cache_key] = MCQ.objects.filter(
                created_by=self.teacher
            ).count()
        return self._cache[cache_key]
    
    def get_qa_count(self):
        from quizzes.models import QuestionAnswer
        cache_key = 'qa_count'
        if cache_key not in self._cache:
            self._cache[cache_key] = QuestionAnswer.objects.filter(
                created_by=self.teacher
            ).count()
        return self._cache[cache_key]
    
    def get_tf_count(self):
        from quizzes.models import TrueFalseQuiz
        cache_key = 'tf_count'
        if cache_key not in self._cache:
            self._cache[cache_key] = TrueFalseQuiz.objects.filter(
                created_by=self.teacher
            ).count()
        return self._cache[cache_key]
    
    def get_average_mcq_score(self):
        """Score moyen aux QCM pour les étudiants des niveaux enseignés"""
        cache_key = 'avg_mcq'
        if cache_key not in self._cache:
            unites = self.get_teaching_unites()
            levels = [unite.level for unite in unites if unite.level]
            
            if not levels:
                self._cache[cache_key] = 0
            else:
                # Récupérer les étudiants des niveaux concernés
                students = self.get_students()
                
                result = MCQResult.objects.filter(
                    student__in=students
                ).aggregate(avg=Avg('score'))
                self._cache[cache_key] = result['avg'] or 0
        return self._cache[cache_key]
    
    def get_average_qa_score(self):
        cache_key = 'avg_qa'
        if cache_key not in self._cache:
            students = self.get_students()
            result = QAResult.objects.filter(
                student__in=students
            ).aggregate(avg=Avg('score'))
            self._cache[cache_key] = result['avg'] or 0
        return self._cache[cache_key]
    
    def get_average_tf_score(self):
        cache_key = 'avg_tf'
        if cache_key not in self._cache:
            students = self.get_students()
            result = TrueFalseResult.objects.filter(
                student__in=students
            ).aggregate(avg=Avg('score'))
            self._cache[cache_key] = result['avg'] or 0
        return self._cache[cache_key]
    
    def get_recent_activity(self, days=7):
        """Activité récente des étudiants"""
        cache_key = f'recent_activity_{days}'
        if cache_key not in self._cache:
            since_date = timezone.now() - timedelta(days=days)
            students = self.get_students()
            
            mcq_attempts = MCQResult.objects.filter(
                student__in=students,
                created_at__gte=since_date
            ).count()
            
            qa_attempts = QAResult.objects.filter(
                student__in=students,
                created_at__gte=since_date
            ).count()
            
            tf_attempts = TrueFalseResult.objects.filter(
                student__in=students,
                created_at__gte=since_date
            ).count()
            
            self._cache[cache_key] = {
                'mcq': mcq_attempts,
                'qa': qa_attempts,
                'tf': tf_attempts,
                'total': mcq_attempts + qa_attempts + tf_attempts
            }
        return self._cache[cache_key]
    
    def get_chapter_completion_rate(self):
        """Taux de complétion des chapitres - basé sur les niveaux"""
        cache_key = 'completion_rate'
        if cache_key not in self._cache:
            unites = self.get_teaching_unites()
            levels = [unite.level for unite in unites if unite.level]
            
            if not levels:
                self._cache[cache_key] = 0
            else:
                # Récupérer les étudiants concernés
                students = self.get_students()
                total_students = students.count()
                
                if total_students == 0:
                    self._cache[cache_key] = 0
                else:
                    # Récupérer les chapitres des unités enseignées
                    chapters = Chapter.objects.filter(ue__in=unites)
                    
                    # Compter les étudiants qui ont au moins une tentative
                    students_with_activity = set()
                    
                    for result_model in [MCQResult, QAResult, TrueFalseResult]:
                        for student_id in result_model.objects.filter(
                            student__in=students,
                            chapter__in=chapters
                        ).values_list('student_id', flat=True).distinct():
                            students_with_activity.add(student_id)
                    
                    completed = len(students_with_activity)
                    self._cache[cache_key] = (completed / total_students) * 100 if total_students > 0 else 0
        return self._cache[cache_key]
    
    def get_score_distribution(self):
        """Distribution des scores"""
        cache_key = 'score_distribution'
        if cache_key not in self._cache:
            distribution = {
                '0-20': 0, '21-40': 0, '41-60': 0, '61-80': 0, '81-100': 0
            }
            
            students = self.get_students()
            
            # Collecter tous les scores
            scores = []
            for result_model in [MCQResult, QAResult, TrueFalseResult]:
                scores.extend(result_model.objects.filter(
                    student__in=students
                ).values_list('score', flat=True))
            
            for score in scores:
                if score <= 20:
                    distribution['0-20'] += 1
                elif score <= 40:
                    distribution['21-40'] += 1
                elif score <= 60:
                    distribution['41-60'] += 1
                elif score <= 80:
                    distribution['61-80'] += 1
                else:
                    distribution['81-100'] += 1
            
            self._cache[cache_key] = distribution
        return self._cache[cache_key]
    
    def get_top_students(self, limit=10):
        """Meilleurs étudiants"""
        cache_key = f'top_students_{limit}'
        if cache_key not in self._cache:
            students = self.get_students()
            student_scores = []
            
            for student in students:
                # Calculer le score moyen de l'étudiant
                scores = []
                for result_model in [MCQResult, QAResult, TrueFalseResult]:
                    avg = result_model.objects.filter(
                        student=student
                    ).aggregate(avg=Avg('score'))['avg']
                    if avg is not None:
                        scores.append(avg)
                
                if scores:
                    avg_score = sum(scores) / len(scores)
                    student_scores.append((student, avg_score))
            
            student_scores.sort(key=lambda x: x[1], reverse=True)
            self._cache[cache_key] = student_scores[:limit]
        return self._cache[cache_key]
    
    def get_struggling_students(self, limit=10, threshold=50):
        """Étudiants en difficulté (score moyen < threshold)"""
        cache_key = f'struggling_{limit}_{threshold}'
        if cache_key not in self._cache:
            students = self.get_students()
            struggling = []
            
            for student in students:
                scores = []
                for result_model in [MCQResult, QAResult, TrueFalseResult]:
                    avg = result_model.objects.filter(
                        student=student
                    ).aggregate(avg=Avg('score'))['avg']
                    if avg is not None:
                        scores.append(avg)
                
                if scores:
                    avg_score = sum(scores) / len(scores)
                    if avg_score < threshold:
                        struggling.append((student, avg_score))
            
            struggling.sort(key=lambda x: x[1])
            self._cache[cache_key] = struggling[:limit]
        return self._cache[cache_key]
    
    def get_students_count_by_level(self):
        """Nombre d'étudiants par niveau"""
        unites = self.get_teaching_unites()
        result = {}
        
        for unite in unites:
            if unite.level:
                count = StudentProfile.objects.filter(
                    level=unite.level,
                    user__is_student=True,
                    is_active_student=True
                ).count()
                result[unite.title] = count
        
        return result


def export_results_to_csv(students_data):
    """Exporte les résultats des étudiants en CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Étudiant', 'Email', 'Niveau', 'Score QCM (%)', 'Score QA (%)', 
        'Score V/F (%)', 'Score Global (%)', 'Dernière activité'
    ])
    
    for data in students_data:
        writer.writerow([
            data.get('student_name', ''),
            data.get('email', ''),
            data.get('level', ''),
            data.get('mcq_score', 0),
            data.get('qa_score', 0),
            data.get('tf_score', 0),
            data.get('global_score', 0),
            data.get('last_activity', ''),
        ])
    
    return output.getvalue()

