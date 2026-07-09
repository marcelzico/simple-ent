from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from lecon.models import Unite
from ..decorators import teacher_required, teacher_of_unite_required
from ..forms import UniteForm, UniteTeachersForm
from django.contrib.auth import get_user_model
from student.models import StudentProfile

User = get_user_model()


@login_required
@teacher_required
def unites_list(request):
    """
    Liste des unités enseignées par l'enseignant
    """
    teacher = request.user

    # unite_level = Unite.objects.get()
    # students = StudentProfile.objects.filter(level=unite_level)
    
    # Filtrer les unités où l'enseignant est dans teachers
    unites = Unite.objects.filter(teachers=teacher).annotate(
        chapters_count=Count('chapters', distinct=True),
        # students_count=Count('studentprofile', distinct=True)
    ).order_by('level', 'semester')
    
    # Filtrage
    level_filter = request.GET.get('level')
    if level_filter:
        unites = unites.filter(level=level_filter)
    
    # Pagination
    paginator = Paginator(unites, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Récupérer les choix de niveau pour le filtre
    level_choices = Unite.LEVEL_CHOICES
    
    context = {
        'page_obj': page_obj,
        'unites': page_obj,
        'level_filter': level_filter,
        'level_choices': level_choices,
        'total_unites': unites.count(),
    }
    
    return render(request, 'teacher/unites/liste.html', context)


@login_required
@teacher_required
def unite_create(request):
    """
    Créer une nouvelle unité d'enseignement
    """
    if request.method == 'POST':
        form = UniteForm(request.POST)
        if form.is_valid():
            unite = form.save()
            # Ajouter l'enseignant actuel comme enseignant de l'unité
            unite.teachers.add(request.user)
            messages.success(request, f'Unité "{unite.title}" créée avec succès.')
            return redirect('teacher:unites_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = UniteForm()
    
    context = {
        'form': form,
        'title': 'Créer une unité',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/unites/formulaire.html', context)


@login_required
@teacher_required
@teacher_of_unite_required('pk')
def unite_edit(request, pk):
    """
    Modifier une unité existante
    """
    unite = get_object_or_404(Unite, pk=pk)
    
    if request.method == 'POST':
        form = UniteForm(request.POST, instance=unite)
        if form.is_valid():
            form.save()
            messages.success(request, f'Unité "{unite.title}" modifiée avec succès.')
            return redirect('teacher:unites_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = UniteForm(instance=unite)
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Modifier {unite.title}',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/unites/formulaire.html', context)


@login_required
@teacher_required
@teacher_of_unite_required('pk')
def unite_delete(request, pk):
    """
    Supprimer une unité
    """
    unite = get_object_or_404(Unite, pk=pk)
    
    if request.method == 'POST':
        unite_title = unite.title
        unite.delete()
        messages.success(request, f'Unité "{unite_title}" supprimée avec succès.')
        return redirect('teacher:unites_list')
    
    context = {
        'unite': unite,
        'title': f'Supprimer {unite.title}',
    }
    
    return render(request, 'teacher/unites/supprimer.html', context)


@login_required
@teacher_required
@teacher_of_unite_required('pk')
def unite_teachers_manage(request, pk):
    """
    Gérer les enseignants d'une unité (ajouter/retirer)
    """
    unite = get_object_or_404(Unite, pk=pk)
    
    if request.method == 'POST':
        form = UniteTeachersForm(request.POST, instance=unite)
        if form.is_valid():
            form.save()
            messages.success(request, f'Enseignants de "{unite.title}" mis à jour.')
            return redirect('teacher:unites_list')
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = UniteTeachersForm(instance=unite)
        # Personnaliser le queryset pour les enseignants
        form.fields['teachers'].queryset = User.objects.filter(is_teacher=True)
        form.fields['main_teacher'].queryset = User.objects.filter(is_teacher=True)
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Gérer les enseignants - {unite.title}',
    }
    
    return render(request, 'teacher/unites/gestion_enseignants.html', context)

