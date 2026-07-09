def user_profile(request):
    """Add user profile data to all templates"""
    context = {}
    
    if request.user.is_authenticated:
        user = request.user
        context['current_user'] = user
        
        # Add active profile
        if user.is_teacher and hasattr(user, 'teacher_profile'):
            context['active_profile'] = user.teacher_profile
            context['is_teacher_mode'] = True
        elif user.is_student and hasattr(user, 'student_profile'):
            context['active_profile'] = user.student_profile
            context['is_student_mode'] = True
        
        # Check if user has both roles
        context['has_both_roles'] = user.is_student and user.is_teacher
        
        # Get active role from session
        active_role = request.session.get('active_role')
        if active_role:
            context['active_role'] = active_role
    
    return context