from lecon.models import Unite


def teacher_context(request):
    """
    Context processor pour injecter des variables teacher dans tous les templates
    """
    context = {}
    
    if request.user.is_authenticated and request.user.is_teacher:
        # Récupérer les unités enseignées par l'utilisateur
        teaching_unites = Unite.objects.filter(teachers=request.user)
        
        context.update({
            'teaching_unites': teaching_unites,
            'is_teacher': True,
            'teacher_has_unites': teaching_unites.exists(),
            'teacher_unites_count': teaching_unites.count(),
        })
    
    return context
