from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from lecon.models import Unite, Chapter
from quizlet_copy.models import FlashcardSet, Flashcard, UserProgress
from ..decorators import teacher_required, teacher_of_unite_required
from ..forms import FlashcardSetForm, FlashcardForm


@login_required
@teacher_required
def flashcard_sets_list(request, unite_id=None):
    """Liste des sets de flashcards"""
    teacher = request.user
    teaching_unites = Unite.objects.filter(teachers=teacher)
    
    # Récupérer les sets créés par l'enseignant
    sets = FlashcardSet.objects.filter(
        # created_by=teacher,
        title__ue__in=teaching_unites,
        is_public=True
    ).select_related('title', 'title__ue')
    
    unite = None
    if unite_id:
        unite = get_object_or_404(Unite, pk=unite_id)
        if unite in teaching_unites:
            sets = sets.filter(title__ue=unite)
    
    search_query = request.GET.get('q')
    if search_query:
        sets = sets.filter(
            Q(title__title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    paginator = Paginator(sets, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'sets': page_obj,
        'unite': unite,
        'teaching_unites': teaching_unites,
        'search_query': search_query,
    }
    
    return render(request, 'teacher/flashcards/sets.html', context)


@login_required
@teacher_required
def flashcard_set_create(request, unite_id):
    """Créer un set de flashcards"""
    unite = get_object_or_404(Unite, pk=unite_id)
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        form = FlashcardSetForm(request.POST, teacher=request.user, unite_id=unite_id)
        if form.is_valid():
            flashcard_set = form.save(commit=False)
            flashcard_set.created_by = request.user
            flashcard_set.save()
            messages.success(request, 'Set de flashcards créé avec succès.')
            return redirect('teacher:flashcard_cards', set_id=flashcard_set.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = FlashcardSetForm(teacher=request.user, unite_id=unite_id)
    
    context = {
        'form': form,
        'unite': unite,
        'title': f'Créer un set - {unite.title}',
        'button_text': 'Créer',
    }
    
    return render(request, 'teacher/flashcards/set_form.html', context)


@login_required
@teacher_required
def flashcard_set_edit(request, pk):
    """Modifier un set de flashcards"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        form = FlashcardSetForm(request.POST, instance=flashcard_set, teacher=request.user, unite_id=unite.id)
        if form.is_valid():
            form.save()
            messages.success(request, 'Set modifié avec succès.')
            return redirect('teacher:flashcard_cards', set_id=flashcard_set.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = FlashcardSetForm(instance=flashcard_set, teacher=request.user, unite_id=unite.id)
    
    context = {
        'form': form,
        'set': flashcard_set,
        'unite': unite,
        'title': f'Modifier - {flashcard_set.title.title}',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/flashcards/set_form.html', context)


@login_required
@teacher_required
def flashcard_set_delete(request, pk):
    """Supprimer un set de flashcards"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=pk)
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        set_title = str(flashcard_set.title)
        flashcard_set.delete()
        messages.success(request, f'Set "{set_title}" supprimé avec succès.')
        return redirect('teacher:flashcard_sets', unite_id=unite.id)
    
    context = {
        'set': flashcard_set,
        'unite': unite,
        'title': 'Supprimer le set',
    }
    
    return render(request, 'teacher/flashcards/set_supprimer.html', context)


@login_required
@teacher_required
def flashcard_cards_list(request, set_id):
    """Liste des flashcards d'un set"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=set_id)
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    cards = Flashcard.objects.filter(flashcard_set=flashcard_set).order_by('id')
    
    # Statistiques sur les cartes maîtrisées par les étudiants
    total_students = UserProgress.objects.filter(
        flashcard__flashcard_set=flashcard_set
    ).values('user').distinct().count()
    
    mastered_stats = {}
    for card in cards:
        mastered_count = UserProgress.objects.filter(
            flashcard=card,
            mastered=True
        ).count()
        mastered_stats[card.id] = mastered_count
    
    context = {
        'set': flashcard_set,
        'cards': cards,
        'unite': unite,
        'total_students': total_students,
        'mastered_stats': mastered_stats,
    }
    
    return render(request, 'teacher/flashcards/cartes.html', context)


@login_required
@teacher_required
def flashcard_card_create(request, set_id):
    """Créer une flashcard"""
    flashcard_set = get_object_or_404(FlashcardSet, pk=set_id)
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        form = FlashcardForm(request.POST)
        if form.is_valid():
            card = form.save(commit=False)
            card.flashcard_set = flashcard_set
            card.save()
            messages.success(request, 'Flashcard créée avec succès.')
            return redirect('teacher:flashcard_cards', set_id=flashcard_set.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = FlashcardForm()
    
    context = {
        'form': form,
        'set': flashcard_set,
        'unite': unite,
        'title': 'Ajouter une flashcard',
        'button_text': 'Ajouter',
    }
    
    return render(request, 'teacher/flashcards/carte_form.html', context)


@login_required
@teacher_required
def flashcard_card_edit(request, pk):
    """Modifier une flashcard"""
    card = get_object_or_404(Flashcard, pk=pk)
    flashcard_set = card.flashcard_set
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        form = FlashcardForm(request.POST, instance=card)
        if form.is_valid():
            form.save()
            messages.success(request, 'Flashcard modifiée avec succès.')
            return redirect('teacher:flashcard_cards', set_id=flashcard_set.id)
        else:
            messages.error(request, 'Veuillez corriger les erreurs.')
    else:
        form = FlashcardForm(instance=card)
    
    context = {
        'form': form,
        'card': card,
        'set': flashcard_set,
        'unite': unite,
        'title': 'Modifier la flashcard',
        'button_text': 'Enregistrer',
    }
    
    return render(request, 'teacher/flashcards/carte_form.html', context)


@login_required
@teacher_required
def flashcard_card_delete(request, pk):
    """Supprimer une flashcard"""
    card = get_object_or_404(Flashcard, pk=pk)
    flashcard_set = card.flashcard_set
    unite = flashcard_set.title.ue
    
    if not unite.is_teacher(request.user) and not request.user.is_superuser:
        messages.error(request, 'Accès non autorisé.')
        return redirect('teacher:flashcard_sets')
    
    if request.method == 'POST':
        card_term = card.term[:50]
        card.delete()
        messages.success(request, f'Flashcard "{card_term}..." supprimée.')
        return redirect('teacher:flashcard_cards', set_id=flashcard_set.id)
    
    context = {
        'card': card,
        'set': flashcard_set,
        'unite': unite,
        'title': 'Supprimer la flashcard',
    }
    
    return render(request, 'teacher/flashcards/carte_supprimer.html', context)

