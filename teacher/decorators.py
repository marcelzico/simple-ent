from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from functools import wraps
from lecon.models import Unite


def teacher_required(function=None, redirect_field_name=None, login_url='login'):
    """
    Décorateur pour vérifier que l'utilisateur est un enseignant
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_teacher or u.is_superuser),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator


def teacher_of_unite_required(unite_id_param='pk'):
    """
    Décorateur pour vérifier que l'enseignant a accès à l'unité spécifiée.
    Usage: @teacher_of_unite_required(unite_id_param='unite_id')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Vous devez être connecté.")
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_teacher:
                raise PermissionDenied("Vous n'êtes pas autorisé à accéder à cette page.")
            
            # Récupérer l'ID de l'unité depuis les kwargs
            unite_id = kwargs.get(unite_id_param)
            if not unite_id:
                # Peut-être que l'ID est passé comme premier argument après request
                if len(args) > 0:
                    unite_id = args[0]
            
            if unite_id:
                unite = get_object_or_404(Unite, pk=unite_id)
                if not unite.is_teacher(request.user):
                    raise PermissionDenied(
                        "Vous n'êtes pas autorisé à modifier cette unité d'enseignement."
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def teacher_owns_chapter_required():
    """
    Décorateur pour vérifier que l'enseignant possède le chapitre via son unité
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied("Vous devez être connecté.")
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            if not request.user.is_teacher:
                raise PermissionDenied("Vous n'êtes pas autorisé.")
            
            chapter_id = kwargs.get('chapter_id') or kwargs.get('pk')
            if chapter_id:
                from lecon.models import Chapter
                chapter = get_object_or_404(Chapter, pk=chapter_id)
                if not chapter.ue.is_teacher(request.user):
                    raise PermissionDenied(
                        "Vous n'êtes pas autorisé à modifier ce chapitre."
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

