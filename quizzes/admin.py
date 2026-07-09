from django.contrib import admin
from .models import MCQ, QuestionAnswer, MCQQuiz, QAQuiz, MCQAttempt, QAAttempt, StudentAnswer, MCQResult, QAAnswer, QAResult, TrueFalseQuiz, TrueFalseResult


# -----------------MCQ---------------------
@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'question', 'correct_option')
    search_fields = ('chapter', 'question')

@admin.register(MCQResult)
class MCQResultAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'student', 'score')
    readonly_fields = ('chapter', 'student', 'score')
    search_fields = ('chapter', 'student')


# ----------------MCQ QUIZ ----------------
@admin.register(MCQQuiz)
class MCQQuizAdmin(admin.ModelAdmin):
    list_display = ('subject', 'title', 'score_to_pass', 'start_date', 'end_date')
    search_fields = ('subject', 'title')
    list_filter = ('subject', 'start_date', 'end_date')

@admin.register(MCQAttempt)
class MCQAttemptAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'student', 'score', 'completed')
    list_filter = ('quiz', 'student')
    search_fields = ('quiz', 'student')
    readonly_fields = ('quiz', 'student', 'score')


# -------------------QA----------------------
@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'question', 'sample_answer')
    search_fields = ('chapter', 'question', 'sample_answer')

@admin.register(QAAnswer)
class QAAnswerAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'student', 'question', 'answer')
    readonly_fields = ('chapter', 'student', 'answer')
    search_fields = ('chapter', 'student')

@admin.register(QAResult)
class QAResultAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'student', 'score')
    readonly_fields = ('chapter', 'student', 'score')
    search_fields = ('chapter', 'student')


# ---------------- QA QUIZ ------------------
@admin.register(QAQuiz)
class QAQuizAdmin(admin.ModelAdmin):
    list_display = ('subject', 'title', 'score_to_pass', 'start_date', 'end_date')
    search_fields = ('subject', 'title')
    list_filter = ('subject', 'start_date', 'end_date')

@admin.register(StudentAnswer)
class StudentAnswerAdmin(admin.ModelAdmin):
    list_display = ('attempt', 'question', 'similarity_score', 'teacher_mark')
    readonly_fields = ('attempt', 'similarity_score', 'teacher_mark')

@admin.register(QAAttempt)
class QAAttemptAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'student', 'score', 'teacher_score', 'completed')
    list_filter = ('quiz', 'student')
    search_fields = ('quiz', 'student')
    readonly_fields = ('student', 'score', 'teacher_score')


# ---------------TRUE OR FALSE --------------------
@admin.register(TrueFalseQuiz)
class TrueFalseQuizAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'question', 'answer')
    search_fields = ('chapter', 'question')

@admin.register(TrueFalseResult)
class TrueFalseResultAdmin(admin.ModelAdmin):
    list_display = ('chapter', 'student', 'score')
    readonly_fields = ('chapter', 'student', 'score')
    search_fields = ('chapter', 'student')


