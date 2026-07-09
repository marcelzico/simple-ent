from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from lecon.models import Unite, Chapter
from ..decorators import teacher_required, teacher_of_unite_required, teacher_owns_chapter_required
from ..forms import ChapterForm
from django.http import JsonResponse


@login_required
@teacher_required
def chapitres_list(request, unite_id):
    """
    Liste des chapitres d'une unité
    """
    unite = get_object_or_404(Unite, pk=unite_id)
    
    # Vérifier que l'enseignant a accès à cette unité
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Vous n\'avez pas accès à cette unité.')
        return redirect('teacher:unites_list')
    
    chapitres = Chapter.objects.filter(ue=unite).order_by('order', 'id')
    
    # Filtrage
    is_active_filter = request.GET.get('is_active')
    if is_active_filter == 'active':
        chapitres = chapitres.filter(is_active=True)
    elif is_active_filter == 'inactive':
        chapitres = chapitres.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(chapitres, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'unite': unite,
        'page_obj': page_obj,
        'chapitres': page_obj,
        'is_active_filter': is_active_filter,
        'total_chapitres': chapitres.count(),
    }
    
    return render(request, 'teacher/chapitres/liste.html', context)


@login_required
@teacher_required
@teacher_of_unite_required('unite_id')
def chapitre_create(request, unite_id):
    """
    Créer un chapitre dans une unité
    """
    unite = get_object_or_404(Unite, pk=unite_id)
    
    if request.method == 'POST':
        form = ChapterForm(request.POST)
        if form.is_valid():
            chapitre = form.save(commit=False)
            chapitre.ue = unite
            chapitre.save()
            messages.success(request, f'Chapitre "{chapitre.title}" créé avec succès.')
            return redirect('teacher:chapitres_list', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = ChapterForm()
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Créer un chapitre - {unite.title}',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/chapitres/formulaire.html', context)


@login_required
@teacher_required
@teacher_owns_chapter_required()
def chapitre_edit(request, pk):
    """
    Modifier un chapitre
    """
    chapitre = get_object_or_404(Chapter, pk=pk)
    unite = chapitre.ue
    
    if request.method == 'POST':
        form = ChapterForm(request.POST, instance=chapitre)
        if form.is_valid():
            form.save()
            messages.success(request, f'Chapitre "{chapitre.title}" modifié avec succès.')
            return redirect('teacher:chapitres_list', unite_id=unite.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs ci-dessous.')
    else:
        form = ChapterForm(instance=chapitre)
    
    context = {
        'form': form,
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Modifier {chapitre.title}',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/chapitres/formulaire.html', context)


@login_required
@teacher_required
@teacher_owns_chapter_required()
def chapitre_delete(request, pk):
    """
    Supprimer un chapitre
    """
    chapitre = get_object_or_404(Chapter, pk=pk)
    unite = chapitre.ue
    chapitre_title = chapitre.title
    
    if request.method == 'POST':
        chapitre.delete()
        messages.success(request, f'Chapitre "{chapitre_title}" supprimé avec succès.')
        return redirect('teacher:chapitres_list', unite_id=unite.id)
    
    context = {
        'chapitre': chapitre,
        'unite': unite,
        'title': f'Supprimer {chapitre.title}',
    }
    
    return render(request, 'teacher/chapitres/supprimer.html', context)


@login_required
@teacher_required
def chapitre_reorder(request, unite_id):
    """
    Réordonner les chapitres d'une unité (AJAX)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Méthode non autorisée'}, status=405)
    
    unite = get_object_or_404(Unite, pk=unite_id)
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        return JsonResponse({'error': 'Non autorisé'}, status=403)
    
    import json
    data = json.loads(request.body)
    orders = data.get('orders', {})
    
    for chapter_id, new_order in orders.items():
        Chapter.objects.filter(id=chapter_id, ue=unite).update(order=new_order)
    
    return JsonResponse({'success': True})

