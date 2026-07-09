from django.db import models
from lecon.models import Chapter, Unite
from utilisateur.models import User

class MCQ(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE) #, related_name='mcqs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    option1 = models.CharField(max_length=200)
    option2 = models.CharField(max_length=200)
    option3 = models.CharField(max_length=200, null=True)
    option4 = models.CharField(max_length=200, null=True)
    correct_option = models.PositiveSmallIntegerField(choices=[(1, 'Option 1'), (2, 'Option 2'), (3, 'Option 3'), (4, 'Option 4')])
    explanation = models.TextField(blank=True, null=True)
    time_limit = models.PositiveIntegerField(default=60)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.chapter.title[:20]}... - {self.question}"

    class Meta:
        indexes = [
            # Enhanced indexes
            models.Index(fields=['chapter', '-created_at']),  # Chapter's MCQs by date
            models.Index(fields=['created_by', '-created_at']),  # Creator's MCQs by date
            models.Index(fields=['chapter', 'created_by']),  # Chapter's MCQs by creator
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['-created_at']),  # All MCQs by date

        ]

class MCQResult (models.Model):
    student = models.ForeignKey (User, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField (auto_now_add=True)

    def __str__(self) :
        return f"{self.student} - {self.chapter}"
    
    class Meta:
        ordering = ["-created_at", 'student']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', 'chapter', '-created_at']),  # User's chapter results
            models.Index(fields=['chapter', '-score']),  # Chapter ranking
            models.Index(fields=['student', '-score']),  # User's high scores
            models.Index(fields=['score']),  # Score distribution
            models.Index(fields=['student', 'chapter', 'score']),  # User's chapter performance
            models.Index(fields=['-created_at']),  # Already in ordering but explicit
        ]
 

class QuestionAnswer(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE) #, related_name='question_answers')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.TextField()
    sample_answer = models.TextField(blank=True, null=True)
    explanation = models.TextField (blank=True, null=True)
    time_limit = models.PositiveIntegerField(default=300)  # in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Q&A for {self.chapter.title}"

    class Meta:
        ordering = ["-created_at", 'chapter']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['chapter', '-created_at']),  # Chapter's QAs by date
            models.Index(fields=['created_by', '-created_at']),  # Creator's QAs by date
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['-created_at']),  # Already in ordering but explicit
            models.Index(fields=['chapter', 'created_by', '-created_at']),  # Chapter's creator QAs
        ]


class QAAnswer (models.Model):
    chapter = models.ForeignKey(Chapter, verbose_name=("Chapter"), on_delete=models.CASCADE) #, related_name="QAS")
    question = models.ForeignKey(QuestionAnswer, verbose_name=("Question"), on_delete=models.CASCADE)
    student = models.ForeignKey(User, verbose_name=("Student"), on_delete=models.CASCADE)
    answer = models.TextField()
    created_at = models.TimeField(auto_now_add=True)

    def __str__(self):
        return str(self.question)

    class Meta:
        ordering = ["-created_at", 'chapter']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', '-created_at']),  # Student's answers by date
            models.Index(fields=['chapter', 'student', '-created_at']),  # Student's chapter answers
        ]


class QAResult (models.Model):
    chapter = models.ForeignKey(Chapter, verbose_name=("Chapter"), on_delete=models.CASCADE)
    student = models.ForeignKey(User, verbose_name=("Student"), on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} : {self.score}%"
    
    class Meta:
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', 'chapter', '-created_at']),  # Student's chapter results
            models.Index(fields=['chapter', '-score']),  # Chapter ranking
            models.Index(fields=['student', '-score']),  # Student's high scores
            models.Index(fields=['score']),  # Score distribution
            models.Index(fields=['-created_at']),  # Reverse chronological
            models.Index(fields=['student', 'chapter', 'score']),  # Student's chapter performance
        ]


class MCQQuiz(models.Model):
    subject = models.ForeignKey(Unite, on_delete=models.CASCADE, related_name='mcq_quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    chapters = models.ManyToManyField(Chapter)
    questions = models.ManyToManyField(MCQ)
    time_limit = models.PositiveIntegerField()  # in minutes
    max_attempts = models.PositiveIntegerField(default=1)
    score_to_pass = models.PositiveIntegerField(("Score minimal pour passer le test"))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subject.title} - {self.title}"

    class Meta:
        ordering = ["-created_at", 'subject']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['subject', '-created_at']),  # Subject's quizzes by date
            models.Index(fields=['-start_date']),  # Upcoming quizzes
            models.Index(fields=['end_date']),  # Ending quizzes
            models.Index(fields=['subject', 'start_date', 'end_date']),  # Subject's active quizzes
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['subject', 'title']),  # Subject's specific quiz
            models.Index(fields=['score_to_pass']),  # Difficulty filtering
        ]


class QAQuiz(models.Model):
    subject = models.ForeignKey(Unite, on_delete=models.CASCADE, related_name='qa_quizzes')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    chapters = models.ManyToManyField(Chapter)
    questions = models.ManyToManyField(QuestionAnswer)
    time_limit = models.PositiveIntegerField()  # in minutes
    max_attempts = models.PositiveIntegerField(default=1)
    score_to_pass = models.PositiveIntegerField(("Score minimal pour passer le test"))
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.subject.title} - {self.title}"

    class Meta:
        ordering = ["-created_at", 'subject']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['subject', '-created_at']),  # Subject's quizzes by date
            models.Index(fields=['-start_date']),  # Upcoming quizzes
            models.Index(fields=['end_date']),  # Ending quizzes
            models.Index(fields=['subject', 'start_date', 'end_date']),  # Subject's active quizzes
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['subject', 'title']),  # Subject's specific quiz
            models.Index(fields=['score_to_pass']),  # Difficulty filtering
        ]


class MCQAttempt(models.Model):
    quiz = models.ForeignKey(MCQQuiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcq_attempts')
    score = models.FloatField()
    completed = models.BooleanField(default=False)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.student.username}'s attempt on {self.quiz.title}"

    class Meta:
        ordering = ["student", 'quiz']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', '-start_time']),  # Student's attempts by date
            models.Index(fields=['quiz', '-start_time']),  # Quiz attempts by date
            models.Index(fields=['student', 'quiz', '-start_time']),  # Student's quiz attempts
            models.Index(fields=['completed', 'student']),  # Student's completed attempts
            models.Index(fields=['score']),  # Score distribution
            models.Index(fields=['student', 'score']),  # Student's scores
            models.Index(fields=['quiz', 'score']),  # Quiz scores
        ]


class QAAttempt(models.Model):
    quiz = models.ForeignKey(QAQuiz, on_delete=models.CASCADE, related_name='attempts')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='qa_attempts')
    score = models.FloatField(null=True, blank=True)
    teacher_score = models.FloatField(null=True, blank=True)
    similarity_score = models.FloatField(null=True, blank=True)  # NLP similarity score
    completed = models.BooleanField(default=False)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    answers = models.JSONField(default=dict)  # Stores question IDs and student answers
    
    def __str__(self):
        return f"{self.student.username}'s attempt on {self.quiz.title}"

    class Meta:
        ordering = ["student", 'quiz']
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', '-start_time']),  # Student's attempts by date
            models.Index(fields=['quiz', '-start_time']),  # Quiz attempts by date
            models.Index(fields=['student', 'quiz', '-start_time']),  # Student's quiz attempts
            models.Index(fields=['completed', 'student']),  # Student's completed attempts
            models.Index(fields=['score']),  # Score distribution
            models.Index(fields=['teacher_score']),  # Teacher scores
            models.Index(fields=['similarity_score']),  # Similarity scores
            models.Index(fields=['student', 'completed', '-start_time']),  # Student's completed history
        ] 

class StudentAnswer(models.Model):
    attempt = models.ForeignKey(QAAttempt, on_delete=models.CASCADE, related_name='student_answers')
    question = models.ForeignKey(QuestionAnswer, on_delete=models.CASCADE)
    answer = models.TextField()
    similarity_score = models.FloatField(null=True, blank=True)
    teacher_mark = models.FloatField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    def __str__(self):
        return f"Answer for {self.question.question[:50]}..."

    class Meta:
        ordering = ["attempt"]
        indexes = [
            # Enhanced indexes
            models.Index(fields=['similarity_score']),  # Similarity analysis
            models.Index(fields=['teacher_mark']),  # Teacher marks
            models.Index(fields=['attempt', '-id']),  # Attempt's answers order
        ]


class TrueFalseQuiz (models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE) #, related_name="TFS")
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    question = models.TextField()
    answer = models.BooleanField()
    explanation = models.TextField(blank=True, null=True)
    time_limit = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f" {self.question[:50]}... - {self.answer}"
    
    class Meta:
        verbose_name = 'True or False quiz'
        verbose_name_plural = 'True or False quizzes'
        indexes = [
            # Enhanced indexes
            models.Index(fields=['chapter', '-created_at']),  # Chapter's TF questions by date
            models.Index(fields=['created_by', '-created_at']),  # Creator's TF questions by date
            models.Index(fields=['updated_at']),  # For update tracking
            models.Index(fields=['chapter', 'answer']),  # Chapter's true/false distribution
        ]

class TrueFalseResult (models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chapter} - {self.student} - {self.score}"
    
    class Meta:
        verbose_name = 'True or False result'
        verbose_name_plural = 'True or False results'
        indexes = [
            # Enhanced indexes
            models.Index(fields=['student', 'chapter', '-created_at']),  # Student's chapter results
            models.Index(fields=['chapter', '-score']),  # Chapter ranking
            models.Index(fields=['student', '-score']),  # Student's high scores
            models.Index(fields=['score']),  # Score distribution
            models.Index(fields=['-created_at']),  # Reverse chronological
            models.Index(fields=['student', 'chapter', 'score']),  # Student's chapter performance
        ]